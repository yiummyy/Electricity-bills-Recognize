import yaml
import json
import logging
import re
import asyncio
from typing import Dict, Any, List
from pydantic import ValidationError
import random
import os
from app.core.config import settings
import time
from app.models.extraction import (
    ExtractionResult, UsageDetail, PowerFactorDetail, FundPriceDetail,
    MonthlyBillData,
    BillLineItem, TimeOfUsePrice, TimeOfUseType
)
from app.models.bill import BillData, BillItem
from app.services.ocr_service import ocr_service
from app.services.llm_service import llm_service
from app.services.embedding_service import embedding_service, RecursiveCharacterTextSplitter
from fastapi.concurrency import run_in_threadpool
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

class ElectricityExtractor:
    def __init__(self):
        self.ocr_service = ocr_service
        self.llm_service = llm_service
        # Use shared embedding service instance
        self.embedding_service = embedding_service 
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        
        self.prompts = self._load_prompts()
        self.rules = self._load_rules()

    def _load_prompts(self) -> Dict[str, str]:
        path = os.path.join(settings.BASE_DIR, "app/config/electricity_bill_prompt.yml")
        if not os.path.exists(path):
            logger.error(f"Prompt config not found at {path}")
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_rules(self) -> Dict[str, Any]:
        path = os.path.join(settings.BASE_DIR, "../electricity_rules.json") # Adjust path as needed
        if not os.path.exists(path):
            # Fallback or check alternative location
            path = "electricity_rules.json"
        
        if os.path.exists(path):
             with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _safe_parse_json(self, response_str: str) -> Dict[str, Any]:
        if not response_str:
            return {}

        # 1. Remove all markdown code block markers
        cleaned = response_str.strip()
        cleaned = re.sub(r'```\w*\n?', '', cleaned)
        cleaned = re.sub(r'```', '', cleaned)
        cleaned = cleaned.strip()

        # 2. Find outermost JSON object or array
        start_brace = cleaned.find('{')
        start_bracket = cleaned.find('[')
        end_brace = cleaned.rfind('}')
        end_bracket = cleaned.rfind(']')

        start = -1
        end = -1
        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            start = start_brace
            end = end_brace
        elif start_bracket != -1:
            start = start_bracket
            end = end_bracket

        if start == -1 or end == -1 or end <= start:
            logger.warning("No valid JSON structure found in response")
            return {}

        try:
            json_str = cleaned[start:end + 1]
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {"bills": parsed} if "bills" not in parsed else parsed
            return {}
        except Exception as e:
            logger.error(f"JSON parse failed: {e}. Raw: {cleaned[:200]}...")
            return {}

    async def extract_from_file(self, file_content: bytes, filename: str) -> ExtractionResult:
        logger.info(f"Starting extraction for file: {filename}")
        # 1. OCR (Run in threadpool to avoid blocking event loop)
        logger.info("Calling OCR service...")
        ocr_result = await run_in_threadpool(self.ocr_service.process_file, file_content, filename)
        logger.info("OCR completed.")
        
        # --- Save OCR Result to File ---
        try:
            log_dir = os.path.join(settings.BASE_DIR, "logs", "ocr_results")
            os.makedirs(log_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            json_filename = f"{timestamp}_{filename}.json"
            
            # Create a serializable dict for logging
            # Convert raw_text string to a list of lines for better readability in JSON
            ocr_log_data = ocr_result.model_dump()
            if ocr_log_data.get("raw_text"):
                ocr_log_data["raw_text"] = ocr_log_data["raw_text"].split("\n")

            with open(os.path.join(log_dir, json_filename), "w", encoding="utf-8") as f:
                json.dump(ocr_log_data, f, indent=2, ensure_ascii=False)
            logger.info(f"OCR raw result saved to {json_filename}")
        except Exception as e:
            logger.warning(f"Failed to save OCR raw result: {e}")
        # -------------------------------

        raw_text = ocr_result.raw_text
        
        if not raw_text:
            logger.error("OCR failed to extract text")
            raise ValueError("OCR failed to extract text")

        # 2. RAG Preparation (Chunking)
        logger.info(f"Splitting text (len={len(raw_text)})...")
        chunks = self.text_splitter.split_text(raw_text)
        
        # 3. Extraction Steps
        # Run extractions in parallel to save time
        logger.info("Extracting usage, pf, and fund data in parallel...")
        
        # Check if complex prompt exists
        has_complex_prompt = "complex_bill_prompt" in self.prompts
        
        try:
            tasks = [
                self._extract_section(chunks, "electricity_usage_prompt", raw_text),
                self._extract_section(chunks, "power_factor_prompt", raw_text),
                self._extract_section(chunks, "fund_price_prompt", raw_text)
            ]
            
            if has_complex_prompt:
                tasks.append(self._extract_section(chunks, "complex_bill_prompt", raw_text))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            usage_data = results[0] if not isinstance(results[0], Exception) else {}
            if isinstance(results[0], Exception): logger.error(f"Usage extraction failed: {results[0]}")
            
            pf_data = results[1] if not isinstance(results[1], Exception) else {}
            if isinstance(results[1], Exception): logger.error(f"PF extraction failed: {results[1]}")
            
            fund_data = results[2] if not isinstance(results[2], Exception) else {}
            if isinstance(results[2], Exception): logger.error(f"Fund extraction failed: {results[2]}")
            
            complex_data = {}
            if has_complex_prompt and len(results) > 3:
                complex_data = results[3] if not isinstance(results[3], Exception) else {}
                if isinstance(results[3], Exception): logger.error(f"Complex extraction failed: {results[3]}")
            
        except Exception as e:
            logger.error(f"Parallel extraction failed: {e}")
            usage_data = {}
            pf_data = {}
            fund_data = {}
            complex_data = {}

        # 4. Post-processing & Validation
        logger.info("Validating and Merging multi-month data...")
        monthly_bills = self._merge_and_validate_all(usage_data, pf_data, fund_data)

        # 4.5 Anti-hallucination: filter months not found in OCR text
        monthly_bills = self._filter_hallucinated_months(monthly_bills, raw_text)
        
        # 5. Complex Calculation (if applicable)
        if complex_data and "line_items" in complex_data:
            self._process_complex_bill(monthly_bills, complex_data.get("line_items", []))
        
        logger.info(f"Extraction finished. Found {len(monthly_bills)} bills.")
        
        # Backward compatibility: populate single fields with the first bill if available
        first_usage = monthly_bills[0].usage if monthly_bills else None
        first_pf = monthly_bills[0].power_factor if monthly_bills else None
        first_fund = monthly_bills[0].fund_price if monthly_bills else None

        final_result = ExtractionResult(
            file_name=filename,
            usage=first_usage,
            power_factor=first_pf,
            fund_price=first_fund,
            monthly_bills=monthly_bills
        )

        # --- Save Final Result to File ---
        try:
            log_dir = os.path.join(settings.BASE_DIR, "logs", "final_results")
            os.makedirs(log_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            json_filename = f"{timestamp}_{filename}_final.json"
            
            with open(os.path.join(log_dir, json_filename), "w", encoding="utf-8") as f:
                f.write(final_result.model_dump_json(indent=2))
            logger.info(f"Final extraction result saved to {json_filename}")
        except Exception as e:
            logger.warning(f"Failed to save final result: {e}")
        # ---------------------------------

        return final_result

    def _merge_and_validate_all(self, usage_raw: Dict, pf_raw: Dict, fund_raw: Dict) -> List[MonthlyBillData]:
        """
        Merge separate lists from Usage, PF, and Fund prompts into unified MonthlyBillData objects.
        """
        # 1. Normalize inputs to lists
        usage_list = usage_raw.get("bills", []) if isinstance(usage_raw, dict) else []
        pf_list = pf_raw.get("data", []) if isinstance(pf_raw, dict) else []
        fund_list = fund_raw.get("data", []) if isinstance(fund_raw, dict) else []
        
        # Fallback if LLM returned single object instead of list (legacy behavior safeguard)
        if not usage_list and isinstance(usage_raw, dict) and "billing_period" in usage_raw:
             usage_list = [usage_raw]
             
        # Normalize legacy PF/Fund if they are single objects
        if not pf_list and isinstance(pf_raw, dict) and "month" in pf_raw:
             pf_list = [pf_raw]
        if not fund_list and isinstance(fund_raw, dict) and "month" in fund_raw:
             fund_list = [fund_raw]
        
        # 2. Index by Month (YYYY-MM)
        merged = {}

        def get_month(item, key="billing_period"):
            if not isinstance(item, dict): return None
            m = item.get(key) or item.get("month")
            if not m: return None
            
            # Normalize separators
            m_clean = m.replace("年", "-").replace("月", "").replace("/", "-").strip()
            
            # 1. Try exact YYYY-MM match first (strict)
            if re.match(r'^\d{4}-\d{2}$', m_clean):
                return m_clean
            
            # 2. Handle single digit month: 2024-6 -> 2024-06
            match_single = re.match(r'^(\d{4})-(\d{1})$', m_clean)
            if match_single:
                return f"{match_single.group(1)}-{int(match_single.group(2)):02d}"
            
            # 3. Handle ranges (find all dates YYYY-MM-DD or YYYY-MM)
            # Find full dates first
            dates_full = re.findall(r'(\d{4}-\d{1,2})-\d{1,2}', m_clean)
            if dates_full:
                last_date = dates_full[-1] # e.g. "2024-6" or "2024-06"
                # Normalize again
                parts = last_date.split('-')
                if len(parts) == 2:
                    return f"{parts[0]}-{int(parts[1]):02d}"
                return last_date

            # 4. Fallback: find any YYYY-MM or YYYY-M pattern
            match = re.search(r'(\d{4})-(\d{1,2})', m_clean)
            if match:
                return f"{match.group(1)}-{int(match.group(2)):02d}"
            
            # 5. Handle pure YYYYMM (e.g. 202406)
            match_compact = re.search(r'(\d{4})(\d{2})', m_clean)
            if match_compact:
                # Validate month range
                mm = int(match_compact.group(2))
                if 1 <= mm <= 12:
                    return f"{match_compact.group(1)}-{mm:02d}"

            return None
            
        # Process Usage (Primary Source)
        for idx, item in enumerate(usage_list):
            m = get_month(item, "billing_period")
            if not m: 
                # Fallback strategy: If month extraction fails, try to use start_date or end_date
                s = get_month(item, "start_date")
                e = get_month(item, "end_date")
                if s: m = s
                elif e: m = e
                else:
                    # Last resort: use index to preserve data
                    m = f"Unknown-Month-{idx+1}"
                    logger.warning(f"Could not extract month for usage item {idx}, using placeholder {m}")

            if m not in merged:
                merged[m] = {"usage": item, "pf": {}, "fund": {}}
            else:
                merged[m]["usage"] = item
        
        # Process PF
        for idx, item in enumerate(pf_list):
            m = get_month(item, "month")
            if not m: 
                # Try to fuzzy match by index if counts match? 
                # For now, just log and skip or use placeholder
                # But PF data is secondary, so maybe safer to skip if not matchable
                continue 

            if m in merged:
                merged[m]["pf"] = item
            else: # Orphan PF data, maybe new month?
                merged[m] = {"usage": {}, "pf": item, "fund": {}}

        # Process Fund
        for idx, item in enumerate(fund_list):
            m = get_month(item, "month")
            if not m: continue
            if m in merged:
                merged[m]["fund"] = item
            else:
                merged[m] = {"usage": {}, "pf": {}, "fund": item}

        # 3. Validate and Build Objects
        results = []
        for month, data in sorted(merged.items()):
            # Validate sub-models
            u_model = self._validate_usage(data.get("usage", {}))
            p_model = self._validate_pf(data.get("pf", {}))
            f_model = self._validate_fund(data.get("fund", {}))
            
            # Ensure month consistency
            if not p_model.month or p_model.month == "Unknown": p_model.month = month
            if not f_model.month: f_model.month = month
            
            # Create MonthlyBillData
            mb = MonthlyBillData(
                month=month,
                user_id=u_model.user_id,
                usage=u_model,
                power_factor=p_model,
                fund_price=f_model
            )
            results.append(mb)
            
        return results

    def _process_complex_bill(self, monthly_bills: List[MonthlyBillData], line_items_raw: List[Dict]):
        """
        Process complex bill logic:
        1. Parse line items into BillLineItem objects.
        2. Group by TOU type and accumulate unit prices using Decimal for precision.
        3. Distribute shared costs (fund, system op) to all TOU types.
        4. Calculate final prices.
        5. Update ALL monthly_bills with the result.
        """
        if not monthly_bills or not line_items_raw:
            return

        # 1. Parse Items (common for all months)
        line_items = []
        for item in line_items_raw:
            try:
                t_type = item.get("tou_type", "total")
                if t_type not in ["peak", "shoulder", "flat", "valley", "total"]:
                    t_type = "total"

                line_item = BillLineItem(
                    category=item.get("category", "其它"),
                    item_name=item.get("item_name", "未知项目"),
                    tou_type=TimeOfUseType(t_type),
                    usage=float(item.get("usage", 0.0)),
                    unit_price=float(item.get("unit_price", 0.0)),
                    cost=float(item.get("cost", 0.0))
                )
                line_items.append(line_item)
            except Exception as e:
                logger.warning(f"Failed to parse line item: {item}, error: {e}")

        # 2. Accumulate & Distribute (Use Decimal)
        tou_prices = {
            TimeOfUseType.PEAK: Decimal('0.0'),
            TimeOfUseType.SHOULDER: Decimal('0.0'),
            TimeOfUseType.FLAT: Decimal('0.0'),
            TimeOfUseType.VALLEY: Decimal('0.0')
        }
        tou_components = {
            TimeOfUseType.PEAK: {},
            TimeOfUseType.SHOULDER: {},
            TimeOfUseType.FLAT: {},
            TimeOfUseType.VALLEY: {}
        }
        shared_add_on = Decimal('0.0')
        shared_components = {}
        tou_has_data = set()
        has_shared_data = False

        for idx, item in enumerate(line_items):
            cat = item.category
            price = Decimal(str(item.unit_price))

            if price == 0:
                continue

            is_shared = False
            item_name_str = str(item.item_name)

            if cat == "基金及附加费":
                is_shared = True
            elif cat == "其它" and ("系统运行" in item_name_str or "市场化" in item_name_str or "损益" in item_name_str or "分摊" in item_name_str):
                is_shared = True
            elif ("系统运行" in item_name_str or "市场化" in item_name_str or "损益" in item_name_str or "分摊" in item_name_str):
                is_shared = True
            elif ("输配" in item_name_str or "线损" in item_name_str) and item.tou_type == TimeOfUseType.TOTAL:
                is_shared = True
            elif item.tou_type == TimeOfUseType.TOTAL and cat in ["输配电费", "上网环节线损电费"]:
                is_shared = True

            # Fallback: Calculate unit price if missing but cost/usage exists
            if price == 0 and item.cost > 0 and item.usage > 0:
                try:
                    price = Decimal(str(item.cost)) / Decimal(str(item.usage))
                    logger.info(f"Calculated missing unit price for {item.item_name}: {price}")
                except:
                    pass

            # If usage is 0, force unit_price to 0
            if item.usage == 0:
                price = Decimal('0.0')
                logger.info(f"Zero usage detected for {item.item_name}, forcing price to 0.")

            if price == 0:
                continue

            if is_shared:
                shared_add_on += price
                has_shared_data = True
                key = item.item_name
                current_val = Decimal(str(shared_components.get(key, 0.0)))
                shared_components[key] = float(current_val + price)
                logger.info(f"Shared cost added: {key} = {price}")
            else:
                if item.tou_type in tou_prices:
                    tou_prices[item.tou_type] += price
                    tou_has_data.add(item.tou_type)
                    key = f"{cat}-{item.item_name}"
                    current_val = Decimal(str(tou_components[item.tou_type].get(key, 0.0)))
                    tou_components[item.tou_type][key] = float(current_val + price)
                    logger.info(f"TOU cost added to {item.tou_type}: {key} = {price}")

        # 3. Final Calculation & apply to ALL months
        detailed_prices = []
        for t_type in [TimeOfUseType.PEAK, TimeOfUseType.SHOULDER, TimeOfUseType.FLAT, TimeOfUseType.VALLEY]:
            base_price = tou_prices[t_type]
            final_price = base_price + shared_add_on
            final_price_rounded = final_price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            final_price_float = float(final_price_rounded)

            comps = tou_components[t_type].copy()
            comps.update(shared_components)

            detailed_prices.append(TimeOfUsePrice(
                tou_type=t_type,
                final_price=final_price_float,
                components=comps
            ))

            # Apply to ALL months, but only if complex bill contributed data for this TOU type
            # or if shared data exists that affects all TOU types
            for target_bill in monthly_bills:
                # Only overwrite existing price if complex bill actually contributed TOU data
                if t_type not in tou_has_data and not has_shared_data:
                    continue
                if t_type == TimeOfUseType.PEAK:
                    target_bill.usage.peak_price = final_price_float
                elif t_type == TimeOfUseType.SHOULDER:
                    target_bill.usage.shoulder_price = final_price_float
                elif t_type == TimeOfUseType.FLAT:
                    target_bill.usage.flat_price = final_price_float
                elif t_type == TimeOfUseType.VALLEY:
                    target_bill.usage.valley_price = final_price_float

            logger.info(f"Final price for {t_type}: {base_price} + {shared_add_on} = {final_price_rounded}")

        # Apply raw_line_items and detailed_prices to all months
        for target_bill in monthly_bills:
            target_bill.raw_line_items = line_items
            target_bill.detailed_prices = detailed_prices

    async def _extract_section(self, chunks: List[str], prompt_key: str, full_text: str) -> Dict:
        # Improved RAG/Context Management:
        # Increase context window to 32000 chars to handle multi-month bills.
        # Only truncate if absolutely necessary.
        
        context = full_text
        if len(full_text) > 32000:
            logger.info(f"Text too long ({len(full_text)}), performing chunk selection...")
            keywords = []
            if "usage" in prompt_key:
                keywords = ["电量", "电费", "示数", "尖时", "尖峰", "谷段", "账单", "年月"]
            elif "power_factor" in prompt_key:
                keywords = ["功率因数", "考核", "标准", "年月"]
            elif "fund" in prompt_key:
                keywords = ["基金", "附加", "单价", "输配", "年月"]
            
            # Select chunks but maintain order
            relevant_chunks = [c for c in chunks if any(k in c for k in keywords)]
            if not relevant_chunks:
                relevant_chunks = chunks[:5] 
            context = "\n...\n".join(relevant_chunks)

        prompt_template = self.prompts.get(prompt_key, "")
        final_prompt = f"{prompt_template}\n\nContext:\n{context}"
        
        try:
            response_str = await self.llm_service._call_llm(final_prompt)
            
            # --- Save LLM Response to File ---
            try:
                log_dir = os.path.join(settings.BASE_DIR, "logs", "llm_responses")
                os.makedirs(log_dir, exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                suffix = random.randint(1000, 9999)
                filename = f"{timestamp}_{prompt_key}_{suffix}.json"
                
                with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
                    f.write(response_str)
            except Exception as e:
                logger.warning(f"Failed to save LLM response log: {e}")
            # ---------------------------------

            # The prompt now returns {"bills": [...]} or {"data": [...]}
            # We need to parse this and return the raw dict (containing list)
            return self._safe_parse_json(response_str)
        except Exception as e:
            logger.error(f"Extraction failed for {prompt_key}: {e}")
            return {}

    def _filter_hallucinated_months(self, monthly_bills: List[MonthlyBillData], raw_text: str) -> List[MonthlyBillData]:
        """
        Anti-hallucination guard: filter out months that have no evidence in the OCR text.
        Extracts all YYYY-MM patterns from the OCR text and only keeps months that match.
        If no months are found in the OCR text, returns all bills unchanged (fail-open).
        If only 1-2 bills were returned, skip filtering (likely legitimate single/double-month bill).
        """
        if len(monthly_bills) <= 2:
            return monthly_bills

        # Find all billing periods mentioned in OCR text
        # Patterns: "2024-02", "202402", "2024年02月", "20240201-20240301"
        ocr_months = set()
        # YYYY-MM
        for m in re.finditer(r'(\d{4})-(\d{1,2})', raw_text):
            yr, mo = m.group(1), m.group(2)
            ocr_months.add(f"{yr}-{int(mo):02d}")
        # YYYY年M月
        for m in re.finditer(r'(\d{4})年(\d{1,2})月', raw_text):
            ocr_months.add(f"{m.group(1)}-{int(m.group(2)):02d}")
        # YYYYMM (compact)
        for m in re.finditer(r'(\d{4})(\d{2})', raw_text):
            mm = int(m.group(2))
            if 1 <= mm <= 12:
                ocr_months.add(f"{m.group(1)}-{mm:02d}")

        logger.info(f"Anti-hallucination: OCR months found: {sorted(ocr_months)}")
        logger.info(f"Anti-hallucination: LLM returned {len(monthly_bills)} months")

        if not ocr_months:
            logger.warning("No months found in OCR text, skipping hallucination filter")
            return monthly_bills

        filtered = [b for b in monthly_bills if b.month in ocr_months]
        removed = len(monthly_bills) - len(filtered)

        if removed > 0:
            logger.warning(
                f"Anti-hallucination: Removed {removed} month(s) not found in OCR text. "
                f"Filtered months: {[b.month for b in monthly_bills if b.month not in ocr_months]}"
            )

        if not filtered:
            logger.error("Anti-hallucination: ALL months filtered! Falling back to original data.")
            return monthly_bills

        return filtered

    def _validate_usage(self, data: Dict) -> UsageDetail:
        # Apply defaults and rules
        defaults = self.rules.get("default_values", {})
        for k, v in defaults.items():
            if data.get(k) is None:
                data[k] = v

        required_floats = [
            "peak_usage", "peak_price", "shoulder_usage", "shoulder_price",
            "flat_usage", "flat_price", "valley_usage", "valley_price",
            "total_usage", "total_cost"
        ]
        for f in required_floats:
            if data.get(f) is None:
                data[f] = 0.0
            elif isinstance(data.get(f), str):
                try:
                    data[f] = float(data[f])
                except (ValueError, TypeError):
                    logger.warning(f"Non-numeric value for {f}: {data[f]}, defaulting to 0.0")
                    data[f] = 0.0

        try:
            return UsageDetail(**data)
        except ValidationError as e:
            logger.error(f"UsageDetail validation failed: {e}. Returning defaults.")
            return UsageDetail(
                peak_usage=0.0, peak_price=0.0,
                shoulder_usage=0.0, shoulder_price=0.0,
                flat_usage=0.0, flat_price=0.0,
                valley_usage=0.0, valley_price=0.0,
                total_usage=0.0, total_cost=0.0
            )

    def _validate_pf(self, data: Dict) -> PowerFactorDetail:
        # Check deviation
        std = data.get("standard_pf")
        if std is None:
            std = 0.0
        elif isinstance(std, str):
            try:
                std = float(std.replace("%", ""))
            except (ValueError, TypeError):
                std = 0.0

        act = data.get("actual_pf")
        if act is None:
            act = 0.0
        elif isinstance(act, str):
            try:
                act = float(act.replace("%", ""))
            except (ValueError, TypeError):
                act = 0.0

        data["standard_pf"] = std
        data["actual_pf"] = act

        threshold = self.rules.get("power_factor_warning_threshold", 0.5)
        diff = abs(std - act)
        data["deviation_alert"] = diff > threshold

        if not data.get("month"): data["month"] = "Unknown"
        if not data.get("meter_id"): data["meter_id"] = "Unknown"

        try:
            return PowerFactorDetail(**data)
        except ValidationError as e:
            logger.error(f"PowerFactorDetail validation failed: {e}. Returning defaults.")
            return PowerFactorDetail(
                month=data.get("month", "Unknown"),
                meter_id=data.get("meter_id", "Unknown"),
                standard_pf=0.0,
                actual_pf=0.0,
                deviation_alert=False
            )

    def _validate_fund(self, data: Dict) -> FundPriceDetail:
        # Fill missing with 0.0000
        fields = [
            "fund_surcharge_price", "fund_proxy_price", "transmission_price",
            "loss_price", "system_operation_price", "water_fund_price",
            "rural_loan_fund_price", "reservoir_fund_price", "renewable_energy_price"
        ]
        for f in fields:
            if data.get(f) is None:
                data[f] = 0.0
            elif isinstance(data.get(f), str):
                try:
                    data[f] = float(data[f])
                except (ValueError, TypeError):
                    logger.warning(f"Non-numeric value for {f}: {data[f]}, defaulting to 0.0")
                    data[f] = 0.0

        try:
            return FundPriceDetail(**data)
        except ValidationError as e:
            logger.error(f"FundPriceDetail validation failed: {e}. Returning defaults.")
            return FundPriceDetail(
                fund_surcharge_price=0.0, fund_proxy_price=0.0,
                transmission_price=0.0, loss_price=0.0,
                system_operation_price=0.0, water_fund_price=0.0,
                rural_loan_fund_price=0.0, reservoir_fund_price=0.0,
                renewable_energy_price=0.0
            )

    def _map_to_bill_data(self, usage_data: UsageDetail, pf_data: PowerFactorDetail, fund_data: FundPriceDetail, raw_text: str) -> BillData:
        # Extract basic info from usage data or raw text
        bill = BillData()
        
        # 1. Map Usage Data
        if usage_data:
            bill.user_id = usage_data.user_id
            bill.settlement_account_no = usage_data.settlement_account_no
            bill.meter_no = usage_data.meter_no
            bill.total_usage = usage_data.total_usage
            bill.total_cost = usage_data.total_cost
            
            # Construct items
            # Peak
            if usage_data.peak_usage > 0:
                bill.items.append(BillItem(
                    period="尖时",
                    electricity_usage=usage_data.peak_usage,
                    price=usage_data.peak_price,
                    cost=round(usage_data.peak_usage * usage_data.peak_price, 2)
                ))
                