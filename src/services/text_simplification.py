import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain


def simplify_text(text):
    load_dotenv()

    try:
        chat_model = ChatOpenAI(
            temperature=0,
            model_name="gpt-4o",
            api_key=os.environ.get("OPENAI_API_KEY"),
            timeout=300,  # 5 минут таймаут
            max_retries=3,  # 3 попытки при ошибке
            request_timeout=300,  # 5 минут таймаут запроса
        )

        doc = [Document(page_content=text)]
        prompt_template = """Перепиши текст, упростив его, при этом не используй нумерацию абзацев:
        "{text}".
        """
        prompt = PromptTemplate.from_template(prompt_template)
        llm_chain = LLMChain(llm=chat_model, prompt=prompt)
        stuff_chain = StuffDocumentsChain(
            llm_chain=llm_chain, document_variable_name="text"
        )
        summary = stuff_chain.run(doc)

        if not summary:
            raise ValueError("Модель не вернула упрощенного текста")

        return summary, None
    except Exception as e:
        error_message = f"Ошибка при упрощении текста: {str(e)}"
        return (
            None,
            error_message,
        )
