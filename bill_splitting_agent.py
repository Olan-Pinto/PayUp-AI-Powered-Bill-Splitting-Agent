"""
Object-Oriented Bill Splitting System
A refactored version with proper class hierarchy and separation of concerns
"""

import json
import os
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime
from PIL import Image
import google.generativeai as genai
from google.cloud import storage
from langchain.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import hub
from dotenv import load_dotenv


load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Centralized configuration management"""
    def __init__(self, api_key: str, gcs_credentials_path: Optional[str] = None,
                 gcs_bucket_name: Optional[str] = None):
        self.api_key = api_key
        self.vision_model = 'gemini-2.0-flash'
        self.agent_model = 'gemini-2.0-flash'
        self.temperature = 0
        self.max_agent_iterations = 15
        
        # Google Cloud Storage settings
        self.gcs_credentials_path = gcs_credentials_path
        self.gcs_bucket_name = gcs_bucket_name
        self.gcs_enabled = gcs_credentials_path is not None and gcs_bucket_name is not None
        
        if self.gcs_enabled:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.gcs_credentials_path
        
    def configure_genai(self):
        """Configure Google Generative AI"""
        genai.configure(api_key=self.api_key)


# ============================================================================
# CLOUD STORAGE
# ============================================================================

class CloudStorageManager:
    """Manages Google Cloud Storage operations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        
        if self.config.gcs_enabled:
            self.client = storage.Client()
    
    def upload_file(self, source_file_path: str, destination_blob_name: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to Google Cloud Storage
        
        Args:
            source_file_path: Local path to the file
            destination_blob_name: Name for the file in GCS. If None, generates from filename
            
        Returns:
            GCS URI of uploaded file, or None if upload failed/disabled
        """
        if not self.config.gcs_enabled:
            print("GCS upload is disabled. Skipping upload.")
            return None
        
        if not os.path.exists(source_file_path):
            print(f"Error: File {source_file_path} not found")
            return None
        
        try:
            # Generate destination name if not provided
            if destination_blob_name is None:
                filename = os.path.basename(source_file_path)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                destination_blob_name = f"bills/{timestamp}_{filename}"
            
            # Upload to GCS
            bucket = self.client.bucket(self.config.gcs_bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_path)
            
            gcs_uri = f"gs://{self.config.gcs_bucket_name}/{destination_blob_name}"
            print(f"File uploaded to {gcs_uri}")
            
            return gcs_uri
            
        except Exception as e:
            print(f"Error uploading to GCS: {str(e)}")
            return None
    
    def upload_with_metadata(self, source_file_path: str, metadata: Dict[str, str],
                            destination_blob_name: Optional[str] = None) -> Optional[str]:
        """
        Upload a file with custom metadata
        
        Args:
            source_file_path: Local path to the file
            metadata: Dictionary of metadata key-value pairs
            destination_blob_name: Name for the file in GCS
            
        Returns:
            GCS URI of uploaded file, or None if upload failed/disabled
        """
        if not self.config.gcs_enabled:
            print("GCS upload is disabled. Skipping upload.")
            return None
        
        if not os.path.exists(source_file_path):
            print(f"Error: File {source_file_path} not found")
            return None
        
        try:
            # Generate destination name if not provided
            if destination_blob_name is None:
                filename = os.path.basename(source_file_path)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                destination_blob_name = f"bills/{timestamp}_{filename}"
            
            # Upload to GCS with metadata
            bucket = self.client.bucket(self.config.gcs_bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.metadata = metadata
            blob.upload_from_filename(source_file_path)
            
            gcs_uri = f"gs://{self.config.gcs_bucket_name}/{destination_blob_name}"
            print(f"File uploaded to {gcs_uri} with metadata: {metadata}")
            
            return gcs_uri
            
        except Exception as e:
            print(f"Error uploading to GCS: {str(e)}")
            return None


# ============================================================================
# BILL PROCESSING
# ============================================================================

class BillData:
    """Data class to represent a bill"""
    def __init__(self, data: Dict[str, Any], gcs_uri: Optional[str] = None):
        self.merchant = data.get('merchant', 'Unknown')
        self.date = data.get('date')
        self.items = data.get('items', [])
        self.subtotal = data.get('subtotal', 0)
        self.tax = data.get('tax', 0)
        self.tip = data.get('tip', 0)
        self.total = data.get('total', 0)
        self.raw_data = data
        self.gcs_uri = gcs_uri  # Store the GCS location
        
    def get_item_by_name(self, item_name: str) -> Optional[Dict]:
        """Find an item by name (case-insensitive partial match)"""
        for item in self.items:
            if item_name.lower() in item['name'].lower():
                return item
        return None
    
    def format_summary(self) -> str:
        """Format bill as a readable summary"""
        lines = []
        
        if self.merchant:
            lines.append(f"Merchant: {self.merchant}")
        if self.date:
            lines.append(f"Date: {self.date}")
        if self.gcs_uri:
            lines.append(f"Stored at: {self.gcs_uri}")
            
        lines.append("\nItems:")
        for item in self.items:
            qty = item.get('quantity', 1)
            unit_price = item.get('unit_price', 0)
            total = item.get('total', 0)
            lines.append(f"- {item['name']}: {qty}x ${unit_price} = ${total}")
        
        if self.subtotal:
            lines.append(f"\nSubtotal: ${self.subtotal}")
        if self.tax:
            lines.append(f"Tax: ${self.tax}")
        if self.tip:
            lines.append(f"Tip: ${self.tip}")
            
        lines.append(f"\nTOTAL: ${self.total}")
        
        return '\n'.join(lines)


class BillProcessor(ABC):
    """Abstract base class for bill processing"""
    @abstractmethod
    def process(self, image_path: str) -> BillData:
        """Process a bill image and return structured data"""
        pass


class VisionBillProcessor(BillProcessor):
    """Process bills using Google Gemini Vision API"""
    
    def __init__(self, config: Config, storage_manager: Optional[CloudStorageManager] = None):
        self.config = config
        self.config.configure_genai()
        self.model = genai.GenerativeModel(self.config.vision_model)
        self.storage_manager = storage_manager
        
    def process(self, image_path: str) -> BillData:
        """Process bill image using Gemini Vision and optionally upload to GCS"""
        # Upload to GCS first if enabled
        gcs_uri = None
        if self.storage_manager:
            gcs_uri = self.storage_manager.upload_file(image_path)
        
        # Process the image
        img = Image.open(image_path)
        
        prompt = self._build_prompt()
        response = self.model.generate_content([prompt, img])
        
        raw_data = self._parse_response(response.text)
        return BillData(raw_data, gcs_uri=gcs_uri)
    
    def _build_prompt(self) -> str:
        """Build the vision model prompt"""
        return """Analyze this receipt image and extract:

      - Merchant name
      - Date and time
      - Items purchased (name, quantity, unit price, total)
      - Subtotal, tax, service charges, tips
      - Final total amount

      Pay special attention to:
      - Dollar signs ($) which may look like "5" or "S" in OCR
      - Verify math: items should sum to subtotal/total
      - Use visual context (receipt layout) to identify sections

      Return ONLY valid JSON:
      {
        "merchant": "...",
        "date": "...",
        "items": [{"name": "...", "quantity": 1, "unit_price": 0.00, "total": 0.00}],
        "subtotal": 0.00,
        "tax": 0.00,
        "total": 0.00
      }"""
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse JSON from model response"""
        output = response_text
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()
        
        return json.loads(output)


# ============================================================================
# TOOLS
# ============================================================================

class ToolKit:
    """Collection of mathematical and utility tools"""
    
    @staticmethod
    def calculator(expression: str) -> str:
        """Performs mathematical calculations.
        Input: Math expression like '25.50 + 32.99' or '363.99 / 3'
        """
        try:
            allowed_chars = set('0123456789+-*/(). ')
            if not all(c in allowed_chars for c in expression):
                return "Error: Invalid characters"
            result = eval(expression)
            return str(round(result, 2))
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def split_tax_proportionally(input_string: str) -> str:
        """Split tax/tip proportionally based on subtotals.
        Input format: 'subtotal1,subtotal2,...|tax_amount'
        Example: '25.50,299.00|26.00' means split $26 tax between $25.50 and $299.00 subtotals
        """
        try:
            parts = input_string.split('|')
            if len(parts) != 2:
                return "Error: Format should be 'subtotals|tax' (e.g., '25.50,299.00|26.00')"
            
            person_subtotals = parts[0]
            total_tax = float(parts[1])
            
            subtotals = [float(x.strip()) for x in person_subtotals.split(',')]
            total_subtotal = sum(subtotals)
            tax_shares = [round((s / total_subtotal) * total_tax, 2) for s in subtotals]
            
            return ','.join(map(str, tax_shares))
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def calculate_percentage(input_string: str) -> str:
        """Calculate percentage of an amount.
        Input format: 'amount|percentage'
        Example: '100|30' calculates 30% of 100
        """
        try:
            parts = input_string.split('|')
            if len(parts) != 2:
                return "Error: Format should be 'amount|percentage' (e.g., '100|30')"
            
            amount = float(parts[0])
            percentage = float(parts[1])
            result = (amount * percentage) / 100
            return str(round(result, 2))
        except Exception as e:
            return f"Error: {str(e)}"
    
    @classmethod
    def create_langchain_tools(cls, bill_data: BillData):
        """Create LangChain-compatible tools with bill data context"""
        
        @tool
        def calculator(expression: str) -> str:
            """Performs mathematical calculations."""
            return cls.calculator(expression)
        
        @tool
        def split_tax_proportionally(input_string: str) -> str:
            """Split tax/tip proportionally based on subtotals."""
            return cls.split_tax_proportionally(input_string)
        
        @tool
        def calculate_percentage(input_string: str) -> str:
            """Calculate percentage of an amount."""
            return cls.calculate_percentage(input_string)
        
        @tool
        def item_lookup(item_name: str) -> str:
            """Look up item details from the bill.
            Input: Name of the item (e.g., 'T-Shirt', 'Watches')
            """
            item = bill_data.get_item_by_name(item_name)
            if item:
                return json.dumps({
                    "name": item['name'],
                    "quantity": item.get('quantity', 1),
                    "unit_price": item.get('unit_price'),
                    "total": item.get('total', 0)
                })
            return f"Item '{item_name}' not found"
        
        return [calculator, split_tax_proportionally, calculate_percentage, item_lookup]


# ============================================================================
# EXPENSE SPLITTING
# ============================================================================

class SplitResult:
    """Data class for expense split results"""
    def __init__(self, data: Dict[str, Any]):
        self.split_type = data.get('split_type', 'unknown')
        self.breakdown = data.get('breakdown', [])
        self.verification = data.get('verification', {})
        self.raw_data = data
        
    def to_json(self, indent: int = 2) -> str:
        """Convert to formatted JSON string"""
        return json.dumps(self.raw_data, indent=indent)
    
    def is_valid(self) -> bool:
        """Check if the split is mathematically valid"""
        if not self.verification:
            return False
        
        sum_total = self.verification.get('sum', 0)
        bill_total = self.verification.get('bill_total', 0)
        
        if bill_total is None:
            return True
        
        return abs(sum_total - bill_total) < 0.01


class ExpenseSplitter:
    """Handles expense splitting logic using LangChain agents"""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm = ChatGoogleGenerativeAI(
            model=self.config.agent_model,
            google_api_key=self.config.api_key,
            temperature=self.config.temperature
        )
    
    def split(self, bill_data: BillData, instruction: str) -> SplitResult:
        """Calculate expense split based on user instruction"""
        
        # Create tools with bill context
        tools = ToolKit.create_langchain_tools(bill_data)
        
        # Create agent
        agent = self._create_agent(tools)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=self.config.max_agent_iterations
        )
        
        # Build and execute prompt
        prompt = self._build_prompt(bill_data, instruction)
        response = agent_executor.invoke({"input": prompt})
        
        # Parse response
        result_data = self._parse_response(response['output'])
        return SplitResult(result_data)
    
    def _create_agent(self, tools: List):
        """Create ReAct agent with tools"""
        prompt = hub.pull("hwchase17/react")
        return create_react_agent(self.llm, tools, prompt)
    
    def _build_prompt(self, bill_data: BillData, instruction: str) -> str:
        """Build agent prompt"""
        bill_summary = bill_data.format_summary()
        
        return f"""You are an expense splitting calculator with access to tools.

BILL:
{bill_summary}

USER INSTRUCTION: {instruction}

YOUR TOOLS:
1. item_lookup(item_name) - Get item details
   Example: item_lookup("T-Shirt")

2. calculator(expression) - Do math
   Example: calculator("25.50 + 2.04")

3. split_tax_proportionally(input_string) - Split tax proportionally
   Format: "subtotal1,subtotal2,...|tax_amount"
   Example: split_tax_proportionally("25.50,299.00|26.00")
   This splits $26 tax between $25.50 and $299.00 proportionally

4. calculate_percentage(input_string) - Calculate percentage
   Format: "amount|percentage"
   Example: calculate_percentage("100|30") for 30% of 100

TASK:
1. Look up item prices using item_lookup()
2. Calculate each person's subtotal using calculator()
3. If there's tax/tip, split it using split_tax_proportionally()
4. Add tax shares to subtotals to get final totals

Return your final answer as ONLY valid JSON:
{{
  "split_type": "item_based|equal|percentage|custom",
  "breakdown": [
    {{"person": "Name", "items": ["..."], "subtotal": 0.00, "tax_share": 0.00, "total": 0.00}}
  ],
  "verification": {{"sum": 0.00, "bill_total": {bill_data.total}}}
}}

Work step by step using tools, then provide final JSON."""
    
    def _parse_response(self, output: str) -> Dict:
        """Parse JSON from agent response"""
        print(f"\nFinal output:\n{output}\n")
        
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()
        
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return {
                "error": "Failed to parse JSON",
                "raw_response": output
            }


# ============================================================================
# MAIN SYSTEM
# ============================================================================

class BillSplitSystem:
    """Main orchestrator for the bill splitting system"""
    
    def __init__(self, api_key: str, gcs_credentials_path: Optional[str] = None,
                 gcs_bucket_name: Optional[str] = None):
        self.config = Config(api_key, gcs_credentials_path, gcs_bucket_name)
        
        # Initialize storage manager
        self.storage_manager = CloudStorageManager(self.config) if self.config.gcs_enabled else None
        
        # Initialize processors
        self.bill_processor = VisionBillProcessor(self.config, self.storage_manager)
        self.expense_splitter = ExpenseSplitter(self.config)
    
    def process_and_split(self, image_path: str, instruction: str) -> tuple[BillData, SplitResult]:
        """Process a bill image and split expenses"""
        # Step 1: Extract bill data from image (and upload to GCS)
        print("Processing bill image...")
        bill_data = self.bill_processor.process(image_path)
        
        print("\nBill processed successfully!")
        print(bill_data.format_summary())
        
        # Step 2: Split expenses based on instruction
        print(f"\nSplitting expenses: {instruction}")
        split_result = self.expense_splitter.split(bill_data, instruction)
        
        return bill_data, split_result
    
    def process_and_split_with_metadata(self, image_path: str, instruction: str, 
                                       metadata: Optional[Dict[str, str]] = None) -> tuple[BillData, SplitResult]:
        """Process bill and upload with custom metadata"""
        # Upload with metadata if provided
        if self.storage_manager and metadata:
            gcs_uri = self.storage_manager.upload_with_metadata(image_path, metadata)
            
            # Process without re-uploading
            img = Image.open(image_path)
            prompt = self.bill_processor._build_prompt()
            response = self.bill_processor.model.generate_content([prompt, img])
            raw_data = self.bill_processor._parse_response(response.text)
            bill_data = BillData(raw_data, gcs_uri=gcs_uri)
        else:
            bill_data = self.bill_processor.process(image_path)
        
        print("\nBill processed successfully!")
        print(bill_data.format_summary())
        
        # Split expenses
        print(f"\nSplitting expenses: {instruction}")
        split_result = self.expense_splitter.split(bill_data, instruction)
        
        return bill_data, split_result
    
    def quick_split(self, image_path: str, instruction: str) -> str:
        """Convenience method that returns formatted JSON result"""
        _, split_result = self.process_and_split(image_path, instruction)
        return split_result.to_json()


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Example 1: Basic usage with GCS upload
    system = BillSplitSystem(
        api_key=gemini_api_key,
        gcs_credentials_path=None,
        gcs_bucket_name='uploaded_bills'
    )
    
    # Process and split (automatically uploads to GCS)
    bill_data, split_result = system.process_and_split(
        image_path="test_img.jpg",
        instruction="Olan only bought Paneer Aati. Shivani bought everything else. Split tax proportionally."
    )
    
    # Display results
    print("\n" + "="*60)
    print("FINAL SPLIT RESULT")
    print("="*60)
    print(split_result.to_json())
    
    # Verify split
    if split_result.is_valid():
        print("\nSplit is mathematically valid!")
    else:
        print("\nWarning: Split totals don't match bill total")
    