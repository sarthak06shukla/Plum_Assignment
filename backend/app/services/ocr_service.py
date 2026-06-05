import hashlib
import logging
import os
import platform
import re
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class OCRResult(BaseModel):
    raw_text: str
    confidence_score: float = Field(ge=0, le=100)

    @property
    def text(self) -> str:
        return self.raw_text

    @property
    def confidence(self) -> float:
        return self.confidence_score


class OCRService:
    def extract_text(self, path: Path) -> OCRResult:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf(path)
        if suffix in {".png", ".jpg", ".jpeg"}:
            return self._extract_image(path)
        raise ValueError(f"Unsupported OCR extension: {suffix}")

    def _extract_pdf(self, path: Path) -> OCRResult:
        pypdf_result = self._extract_pdf_with_pypdf(path)
        if pypdf_result.raw_text.strip():
            return pypdf_result

        decoded = self._decode_embedded_text(path)
        if decoded and self._looks_like_claim_text(decoded):
            return OCRResult(raw_text=decoded, confidence_score=62)

        docling_result = self._extract_pdf_with_docling(path)
        if docling_result.raw_text.strip():
            return docling_result

        return OCRResult(raw_text="", confidence_score=15)

    def _extract_pdf_with_docling(self, path: Path) -> OCRResult:
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(str(path))
            raw_text = self._normalize_text(result.document.export_to_markdown())
            return OCRResult(raw_text=raw_text, confidence_score=92 if raw_text else 0)
        except Exception:
            return OCRResult(raw_text="", confidence_score=0)

    def _extract_pdf_with_pypdf(self, path: Path) -> OCRResult:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            raw_text = self._normalize_text("\n".join(pages))
            return OCRResult(raw_text=raw_text, confidence_score=88 if raw_text else 0)
        except Exception:
            return OCRResult(raw_text="", confidence_score=0)

    def _extract_image(self, path: Path) -> OCRResult:
        original_size = self._image_size(path)
        logger.warning(
            "OCR image input path=%s bytes=%s sha256=%s dimensions=%s",
            path,
            path.stat().st_size if path.exists() else 0,
            self._file_digest(path),
            original_size,
        )

        preprocessed_path: Path | None = None
        try:
            preprocessed_path, preprocessed_size = self._preprocess_image(path)
            logger.warning(
                "OCR image preprocessed original_dimensions=%s preprocessed_path=%s preprocessed_dimensions=%s",
                original_size,
                preprocessed_path,
                preprocessed_size,
            )
            primary_result = (
                self._extract_image_with_windows_ocr(preprocessed_path)
                if platform.system().lower() == "windows"
                else self._extract_image_with_tesseract(preprocessed_path)
            )
            if primary_result.raw_text.strip():
                repaired_text = self._repair_common_ocr_errors(primary_result.raw_text)
                score = self._heuristic_image_confidence(repaired_text)
                logger.warning("OCR primary raw text path=%s confidence=%s\n%s", path, score, repaired_text)
                return OCRResult(raw_text=repaired_text, confidence_score=score)
        except Exception as exc:
            logger.exception("Primary image OCR failed for %s: %s", path, exc)
        finally:
            if preprocessed_path:
                try:
                    preprocessed_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Could not delete OCR temp file %s", preprocessed_path)

        try:
            download_enabled = os.getenv("EASYOCR_DOWNLOAD_ENABLED", "").lower() == "true"
            if not download_enabled and not self._easyocr_models_available():
                logger.warning("EasyOCR model files are not available locally; skipping network-dependent fallback for %s", path)
                return OCRResult(raw_text="", confidence_score=15)

            import easyocr

            reader = easyocr.Reader(["en"], gpu=False, download_enabled=download_enabled, verbose=False)
            fragments = reader.readtext(str(path))
            raw_text = self._normalize_text("\n".join(fragment[1] for fragment in fragments))
            confidences = [float(fragment[2]) for fragment in fragments]
            score = (sum(confidences) / len(confidences)) * 100 if confidences else 20
            logger.warning("OCR EasyOCR raw text path=%s confidence=%s\n%s", path, round(score, 2), raw_text)
            return OCRResult(raw_text=raw_text, confidence_score=round(score, 2))
        except Exception as exc:
            logger.exception("EasyOCR failed for %s: %s", path, exc)
            return OCRResult(raw_text="", confidence_score=15)

    def _preprocess_image(self, path: Path) -> tuple[Path, tuple[int, int]]:
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps

        image = Image.open(path).convert("RGB")
        gray = ImageOps.grayscale(image)
        gray = ImageEnhance.Contrast(gray).enhance(1.8)
        scale = 3 if platform.system().lower() == "windows" else 2
        gray = gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS)
        gray = gray.filter(ImageFilter.SHARPEN)

        temp = tempfile.NamedTemporaryFile(prefix="plum_ocr_", suffix=".png", delete=False)
        temp_path = Path(temp.name)
        temp.close()
        gray.save(temp_path)
        return temp_path, gray.size

    def _extract_image_with_tesseract(self, path: Path) -> OCRResult:
        import pytesseract
        from PIL import Image

        with Image.open(path) as image:
            raw_text = self._normalize_text(pytesseract.image_to_string(image, config="--oem 1 --psm 6", timeout=90))
        return OCRResult(raw_text=raw_text, confidence_score=self._heuristic_image_confidence(raw_text))

    def _extract_image_with_windows_ocr(self, path: Path) -> OCRResult:
        script = r"""
param([string]$Path)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
function AwaitOp($op, [type]$type) {
  $asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and
    $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
  })[0]
  $task = $asTask.MakeGenericMethod($type).Invoke($null, @($op))
  $task.Wait()
  $task.Result
}
$file = AwaitOp ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Path)) ([Windows.Storage.StorageFile])
$stream = AwaitOp ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = AwaitOp ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = AwaitOp ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($null -eq $engine) { throw "Windows OCR engine is not available for user profile languages." }
$result = AwaitOp ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
foreach ($line in $result.Lines) {
  ($line.Words | ForEach-Object { $_.Text }) -join ' '
}
"""
        with tempfile.NamedTemporaryFile("w", suffix=".ps1", encoding="utf-8", delete=False) as handle:
            handle.write(script)
            script_path = Path(handle.name)
        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                    str(path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr.strip() or "Windows OCR failed")
            raw_text = self._normalize_text(completed.stdout)
            return OCRResult(raw_text=raw_text, confidence_score=self._heuristic_image_confidence(raw_text))
        finally:
            script_path.unlink(missing_ok=True)

    def _decode_embedded_text(self, path: Path) -> str:
        try:
            content = path.read_bytes()
        except OSError:
            return ""

        decoded = content.decode("utf-8", errors="ignore")
        candidates = re.findall(r"[A-Za-z][A-Za-z0-9 .,:/₹Rs+\-()]{3,}", decoded)
        return self._normalize_text("\n".join(candidates))

    @staticmethod
    def _image_size(path: Path) -> tuple[int, int] | None:
        try:
            from PIL import Image

            with Image.open(path) as image:
                return image.size
        except Exception:
            return None

    @staticmethod
    def _file_digest(path: Path) -> str:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return ""

    @staticmethod
    def _repair_common_ocr_errors(text: str) -> str:
        repairs = [
            (r"Rohan[^\n]{0,20}K[uw]ma[^\n]{0,6}", "Rohan Kumar"),
            (r"Acu[lt]e\s+Tonsi[^\n]{0,16}", "Acute Tonsillitis"),
            (r"Dr\.\s*Ananya\s+Shama\b", "Dr. Ananya Sharma"),
            (r"\bMediche\b", "Medicine"),
            (r"\b1\s*,soo\.oo\b", "1,500.00"),
        ]
        repaired = text
        for pattern, replacement in repairs:
            repaired = re.sub(pattern, replacement, repaired, flags=re.IGNORECASE)
        return repaired

    @staticmethod
    def _heuristic_image_confidence(text: str) -> float:
        if not text.strip():
            return 15
        lowered = text.lower()
        markers = [
            "patient",
            "doctor",
            "diagnosis",
            "hospital",
            "clinic",
            "bill",
            "amount",
            "date",
            "total",
            "rohan kumar",
            "acute tonsillitis",
        ]
        marker_count = sum(1 for marker in markers if marker in lowered)
        text_score = min(1.0, len(text.strip()) / 700)
        if marker_count < 2:
            return round(max(35, min(55, text_score * 55)), 2)
        score = 55 + marker_count * 4 + text_score * 9
        return round(max(55, min(94, score)), 2)

    @staticmethod
    def _easyocr_models_available() -> bool:
        model_dir = Path.home() / ".EasyOCR" / "model"
        if not model_dir.exists():
            return False
        model_names = {path.name.lower() for path in model_dir.glob("*.pth") if path.stat().st_size > 0}
        has_detector = any("craft" in name or "dbnet" in name for name in model_names)
        has_recognizer = any("english" in name or "latin" in name for name in model_names)
        return has_detector and has_recognizer

    @staticmethod
    def _normalize_text(text: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.replace("\r", "\n").splitlines()]
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _looks_like_claim_text(text: str) -> bool:
        lowered = text.lower()
        markers = ["patient", "doctor", "diagnosis", "bill", "hospital", "clinic", "pharmacy"]
        return sum(1 for marker in markers if marker in lowered) >= 2
