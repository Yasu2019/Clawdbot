from taco.controller import TacoController
_controller = TacoController('taco/config.yaml')

def preprocess_before_rag(raw_text: str, domain='document_log') -> str:
    result = _controller.process(raw_text, domain=domain)
    return result['text']
