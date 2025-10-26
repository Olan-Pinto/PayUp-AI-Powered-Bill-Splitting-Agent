import json
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from PIL import Image
import google.generativeai as genai
from langchain.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import hub


class Config:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.vision_model = 'gemini-2.0-flash-exp'
        self.agent_model = 'gemini-2.0-flash'
        self.temperature = 0
        self.max_agent_iterations = 15
        
    def configure_genai(self):
        genai.configure(api_key=self.api_key)

class BillData:
    def __init__(self, data: Dict[str, Any]):
        self.merchant = data.get('merchant', 'Unknown')
        self.date = data.get('date')
        self.items = data.get('items', [])
        self.subtotal = data.get('subtotal', 0)
        self.tax = data.get('tax', 0)
        self.tip = data.get('tip', 0)
        self.total = data.get('total', 0)
        self.raw_data = data
        
    def format_summary(self) -> str:
        lines = []
        lines.append(f"Merchant: {self.merchant}")
        if self.date:
            lines.append(f"Date: {self.date}")
        lines.append("\nItems:")
        for item in self.items:
            lines.append(f"- {item['name']}: {item.get('quantity', 1)}x ${item.get('unit_price', 0)} = ${item.get('total', 0)}")
        lines.append(f"\nSubtotal: ${self.subtotal}")
        lines.append(f"Tax: ${self.tax}")
        lines.append(f"Tip: ${self.tip}")
        lines.append(f"TOTAL: ${self.total}")
        return "\n".join(lines)


class BillProcessor(ABC):
    @abstractmethod
    def process(self, image_path: str) -> BillData:
        pass


class VisionBillProcessor(BillProcessor):
    def __init__(self, config: Config):
        self.config = config
        self.config.configure_genai()
        self.model = genai.GenerativeModel(self.config.vision_model)
        
    def process(self, image_path: str) -> BillData:
        img = Image.open(image_path)
        prompt = self._build_prompt()
        response = self.model.generate_content([prompt, img])
        raw_data = self._parse_response(response.text)
        return BillData(raw_data)
    
    def _build_prompt(self) -> str:
        return """Analyze this receipt image and extract merchant, date, items, subtotal, tax, total.
Return valid JSON only."""

    def _parse_response(self, response_text: str) -> Dict:
        text = response_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)



class ExpenseSplitter:
    def __init__(self, config: Config):
        self.config = config
        self.llm = ChatGoogleGenerativeAI(
            model=self.config.agent_model,
            google_api_key=self.config.api_key,
            temperature=self.config.temperature
        )
    
    def split(self, bill_data: BillData, instruction: str) -> Dict:
        tools = []
        agent = self._create_agent(tools)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=self.config.max_agent_iterations
        )
        prompt = self._build_prompt(bill_data, instruction)
        response = executor.invoke({"input": prompt})
        return self._parse_response(response["output"])
    
    def _create_agent(self, tools):
        prompt = hub.pull("hwchase17/react")
        return create_react_agent(self.llm, tools, prompt)
    
    def _build_prompt(self, bill_data, instruction: str):
        return f"""You are an expense splitting bot. BILL:\n{bill_data.format_summary()}\n
Instruction: {instruction}\nReturn valid JSON only."""
    
    def _parse_response(self, output: str):
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw": output}


class BillSplitSystem:
    def __init__(self, api_key: str):
        self.config = Config(api_key)
        self.bill_processor = VisionBillProcessor(self.config)
        self.expense_splitter = ExpenseSplitter(self.config)
    
    def process_and_split(self, image_path: str, instruction: str):
        bill_data = self.bill_processor.process(image_path)
        split_result = self.expense_splitter.split(bill_data, instruction)
        return bill_data, split_result
