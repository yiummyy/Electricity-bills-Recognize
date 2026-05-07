import queue
import time
import io
import base64
import re
import logging
import threading
from typing import List, Dict, Tuple, Optional
import numpy as np
from PIL import Image
import pdfplumber
from paddleocr import PaddleOCR
from app.models.bill import BillData, BillItem, OCRResult
from app.models.layout import LayoutResult, LayoutItem
from app.core.config import settings
from app.core.scheduler import scheduler  # Use global scheduler

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        # We still maintain a pool of engines matching the max possible concurrency (3)
        # to avoid initialization overhead during resizing.
        # But access to them is gated by the Global Scheduler.
        self.engine_pool = queue.Queue()
        # Initialize 3 engines max to be safe
        for _ in range(3):
            self.engine_pool.put(self._create_engine())
            
    def _create_engine(self):
        return PaddleOCR(
            use_angle_cls=True,
            lang=settings.OCR_LANG
        )
        
    def process_file(self, file_content: bytes, filename: str) -> OCRResult:
        # Wrap the actual work in a lambda for the scheduler
        def _task():
            engine = None
            try:
                # Borrow an engine
                engine = self.engine_pool.get(timeout=10) # Should be available if scheduler lets us in
                
                start_time = time.time()
                file_ext = filename.lower().split('.')[-1]
                
                if file_ext == 'pdf':
                    text, data, image_base64 = self._process_pdf(file_content, engine)
                elif file_ext in ['png', 'jpg', 'jpeg']:
                    text, data, image_base64 = self._process_image(file_content, engine)
                else:
                    raise ValueError(f"Unsupported file type: {file_ext}")
                    
                latency = (time.time() - start_time) * 1000
                
                return OCRResult(
                    raw_text=text,
                    structured_data=data,
                    processing_time_ms=latency
                )
            except Exception as e:
                logger.error(f"Error processing file {filename}: {e}", exc_info=True)
                return OCRResult(
                    raw_text="",
                    structured_data=BillData(),
                    processing_time_ms=0,
                    error=str(e)
                )
            finally:
                if engine:
                    self.engine_pool.put(engine)

        # Submit to global scheduler
        return scheduler.submit(_task)

    def analyze_layout(self, file_content: bytes, filename: str) -> LayoutResult:
        """
        Analyze the layout of the document (PDF first page or Image) and return visualization data.
        """
        def _task():
            engine = None
            try:
                # Borrow an engine
                engine = self.engine_pool.get(timeout=10)
                
                start_time = time.time()
                file_ext = filename.lower().split('.')[-1]
                
                image = None
                image_np = None
                
                import fitz
                
                if file_ext == 'pdf':
                    # Render first page for layout analysis
                    with fitz.open(stream=file_content, filetype="pdf") as doc:
                        if len(doc) > 0:
                            pix = doc[0].get_pixmap(dpi=300)
                            img_data = pix.tobytes("png")
                            image = Image.open(io.BytesIO(img_data))
                            image_np = np.array(image)
                        else:
                            raise ValueError("Empty PDF")
                elif file_ext in ['png', 'jpg', 'jpeg']:
                    image = Image.open(io.BytesIO(file_content))
                    image_np = np.array(image)
                else:
                    raise ValueError(f"Unsupported file type: {file_ext}")
                
                if image is None:
                     raise ValueError("Could not load image from file")

                # Perform OCR
                # result structure: [[[[x1,y1],[x2,y1],[x2,y2],[x1,y2]], (text, conf)], ...]
                result = engine.ocr(image_np, cls=True)
                
                regions = []
                if result and result[0]:
                    for idx, line in enumerate(result[0]):
                        box = line[0]
                        text = line[1][0]
                        confidence = line[1][1]
                        
                        regions.append(LayoutItem(
                            id=idx,
                            box=box,
                            text=text,
                            confidence=confidence,
                            type="text" # Default to text for now
                        ))
                
                # Encode image for frontend
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                return LayoutResult(
                    file_name=filename,
                    image_base64=img_str,
                    image_width=image.width,
                    image_height=image.height,
                    regions=regions,
                    processing_time_ms=(time.time() - start_time) * 1000
                )

            except Exception as e:
                logger.error(f"Layout analysis failed for {filename}: {e}", exc_info=True)
                raise e
            finally:
                if engine:
                    self.engine_pool.put(engine)

        return scheduler.submit(_task)

    def _process_pdf(self, file_content: bytes, ocr_engine: PaddleOCR) -> Tuple[str, BillData, str]:
        """
        Process PDF using pdfplumber for text/tables and PaddleOCR for images inside PDF if needed.
        Ensures all pages are processed even if some are scanned images.
        """
        full_text = ""
        import fitz
        import pdfplumber
        
        # 1. Try extracting structured tables using pdfplumber first (for electronic PDFs)
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = ""
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        page_text += "\n--- Tables ---\n"
                        for table in tables:
                            # Convert table to Markdown format
                            for row in table:
                                # Filter None values and join
                                row_str = " | ".join([str(cell).replace('\n', ' ') if cell else "" for cell in row])
                                page_text += f"| {row_str} |\n"
                            page_text += "\n"
                    
                    # Extract text (layout-preserving)
                    text = page.extract_text(x_tolerance=2, y_tolerance=2)
                    if text:
                        page_text += f"\n--- Text ---\n{text}\n"
                    
                    # If page seems empty or very sparse, mark for OCR
                    if len(page_text.strip()) < 50:
                         page_text = "" # Clear to trigger OCR fallback below
                    
                    if page_text:
                        full_text += f"\n=== Page {i+1} (pdfplumber) ===\n{page_text}"
        except Exception as e:
            logger.error(f"pdfplumber failed: {e}")
            full_text = "" # Reset to force fallback

        # 2. Fallback to Image OCR if text is missing or sparse
        # We use fitz to render images because it's faster/reliable
        if len(full_text.strip()) < 100:
            logger.info("PDF text/tables sparse, falling back to full OCR...")
            full_text = "" # Reset
            doc = fitz.open(stream=file_content, filetype="pdf")
            total_pages = len(doc)
            
            for i, page in enumerate(doc):
                try:
                    logger.info(f"OCRing Page {i+1}/{total_pages}...")
                    pix = page.get_pixmap(dpi=300) # Increase DPI for better accuracy
                    img_data = pix.tobytes("png")
                    
                    # Process image with OCR
                    image = Image.open(io.BytesIO(img_data))
                    image_np = np.array(image)
                    result = ocr_engine.ocr(image_np, cls=True)
                    
                    ocr_text = ""
                    if result and result[0]:
                        # Sort by vertical position (top to bottom) then horizontal (left to right)
                        # PaddleOCR output: [[box, (text, conf)], ...]
                        # box: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                        # Improved Sorting: Bin Y-coordinates to group lines
                        def get_y(item):
                            return item[0][0][1] # y1
                        
                        def get_x(item):
                            return item[0][0][0] # x1

                        # Sort by Y first
                        lines = sorted(result[0], key=get_y)
                        
                        # Group by lines (Y-tolerance 10px)
                        grouped_lines = []
                        if lines:
                            current_line = [lines[0]]
                            current_y = get_y(lines[0])
                            
                            for line in lines[1:]:
                                y = get_y(line)
                                if abs(y - current_y) < 10: # 10px tolerance
                                    current_line.append(line)
                                else:
                                    # Sort current line by X
                                    current_line.sort(key=get_x)
                                    grouped_lines.append(current_line)
                                    current_line = [line]
                                    current_y = y
                            
                            # Add last line
                            current_line.sort(key=get_x)
                            grouped_lines.append(current_line)
                        
                        # Join text
                        ocr_text = ""
                        for line_group in grouped_lines:
                            line_text = " ".join([item[1][0] for item in line_group])
                            ocr_text += line_text + "\n"

                    full_text += f"\n=== Page {i+1} (OCR) ===\n{ocr_text}"
                    
                except Exception as e:
                    logger.error(f"Error OCRing page {i+1}: {e}")
            
            doc.close()

        # Extract data using regex/rules (Fallback/Initial)
        data = self._extract_fields(full_text)
        return full_text, data, ""

    def _process_image(self, file_content: bytes, ocr_engine: PaddleOCR) -> Tuple[str, BillData, str]:
        """
        Process image using PaddleOCR with spatial analysis.
        """
        image = Image.open(io.BytesIO(file_content))
        image_np = np.array(image)
        
        # Use passed engine instance
        result = ocr_engine.ocr(image_np, cls=True)
        
        full_text = ""
        ocr_items = []
        
        if result and result[0]:
            for line in result[0]:
                box = line[0]
                text = line[1][0]
                confidence = line[1][1]
                full_text += text + "\n"
                ocr_items.append({
                    "box": box,
                    "text": text,
                    "conf": confidence,
                    "center": [
                        (box[0][0] + box[2][0]) / 2,
                        (box[0][1] + box[2][1]) / 2
                    ]
                })
        
        # 1. Try regex extraction first
        data = self._extract_fields(full_text)
        
        # 2. Try spatial extraction for missing fields
        self._spatial_extraction(data, ocr_items)
        
        data.confidence_score = 0.95 
        
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        data.legend_image_base64 = img_str
        
        return full_text, data, img_str

    def _spatial_extraction(self, data: BillData, items: List[Dict]):
        """
        Extract values based on spatial proximity to keywords.
        Useful for tabular data where regex fails.
        """
        # Define keywords to look for
        targets = {
            "total_usage": ["总电量", "有功总电量", "合计电量"],
            "total_cost": ["总金额", "合计金额", "应交电费", "金额合计"],
            "user_id": ["户号", "用户编号"],
            "user_name": ["户名", "用户名称"],
        }
        
        # Iterate over targets
        for field, keywords in targets.items():
            # If already extracted, skip
            if getattr(data, field):
                continue
                
            for item in items:
                # Check if item text contains keyword
                if any(kw in item["text"] for kw in keywords):
                    # Look for value in nearby items (right or below)
                    value = self._find_value_near(item, items)
                    if value:
                        try:
                            if field in ["total_usage", "total_cost"]:
                                # Clean number string
                                val_str = re.sub(r"[^\d\.]", "", value)
                                setattr(data, field, float(val_str))
                            else:
                                setattr(data, field, value)
                            break
                        except:
                            pass

    def _find_value_near(self, key_item: Dict, all_items: List[Dict]) -> Optional[str]:
        """
        Find a value item to the right or below the key item.
        """
        key_box = key_item["box"]
        key_center = key_item["center"]
        key_height = key_box[3][1] - key_box[0][1]
        
        candidates = []
        
        for item in all_items:
            if item == key_item:
                continue
                
            item_center = item["center"]
            
            # Check for "Right" neighbor
            # Same row (y-diff small) and to the right (x > key_x)
            y_diff = abs(item_center[1] - key_center[1])
            if y_diff < key_height * 0.5 and item_center[0] > key_center[0]:
                dist = item_center[0] - key_center[0]
                candidates.append({"item": item, "dist": dist, "type": "right"})
                
            # Check for "Below" neighbor
            # Same column (x-diff small) and below (y > key_y)
            x_diff = abs(item_center[0] - key_center[0])
            if x_diff < 50 and item_center[1] > key_center[1]: # 50px tolerance for column alignment
                dist = item_center[1] - key_center[1]
                # Only look at immediate neighbor
                if dist < key_height * 3: 
                    candidates.append({"item": item, "dist": dist, "type": "below"})
        
        # Sort by distance
        candidates.sort(key=lambda x: x["dist"])
        
        if candidates:
            return candidates[0]["item"]["text"]
        return None

    def _extract_fields(self, text: str) -> BillData:
        """
        Rule-based extraction (Regex).
        """
        data = BillData()
        
        # Enhanced Regex Patterns
        patterns = {
            "user_id": [r"户号[:：\s]*(\d+)", r"用户编号[:：\s]*(\d+)"],
            "user_name": [r"户名[:：\s]*([\u4e00-\u9fa5]+)", r"用户名称[:：\s]*([\u4e00-\u9fa5]+)", r"结算户名[:：\s]*([\u4e00-\u9fa5]+)"],
            "address": [r"地址[:：\s]*([\u4e00-\u9fa5\d]+)", r"用电地址[:：\s]*([\u4e00-\u9fa5\d]+)"],
            "total_cost": [r"总金额[:：\s¥]*([\d\.]+)", r"合计金额[:：\s¥]*([\d\.]+)", r"应交电费[:：\s¥]*([\d\.]+)", r"金额合计[:：\s¥]*([\d\.]+)"],
            "total_usage": [r"总电量[:：\s]*([\d\.]+)", r"有功总电量[:：\s]*([\d\.]+)", r"合计电量[:：\s]*([\d\.]+)"],
            "billing_period": [r"计费周期[:：\s]*([\d\.-]+)", r"月份[:：\s]*(\d{4}年\d{1,2}月)"],
            "payment_deadline": [r"截止日期[:：\s]*([\d\.-]+)"]
        }
        
        for field, regex_list in patterns.items():
            for pattern in regex_list:
                match = re.search(pattern, text)
                if match:
                    val = match.group(1)
                    # Simple cleaning
                    if field in ["total_cost", "total_usage"]:
                        try:
                            setattr(data, field, float(val))
                        except:
                            pass
                    else:
                        setattr(data, field, val)
                    break
        
        # Check for missing fields
        required_fields = ["user_id", "total_cost"]
        missing = []
        for f in required_fields:
            if not getattr(data, f):
                missing.append(f)
        
        data.missing_fields = missing
        if missing:
            data.review_flag = True
            data.confidence_score *= 0.8 # Penalize confidence
            
        return data

ocr_service = OCRService()
