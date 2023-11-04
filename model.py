import os
import openai
import sys
import numpy as np
from dotenv import load_dotenv
from langchain.document_loaders import PyPDFDirectoryLoader
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain

def getResponse(question: str, detected_language: str, context: str) -> str:
    """
    Generates a response to the given question using the Langchain ConversationalRetrievalChain class.

    Args:
        question: The question to be answered.
        detected_language: The detected language of the user's input.

    Returns:
        A string containing the response to the question in the detected language.
    """

    # Load the OpenAI API key and the Langchain API key.
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    LANGCHAIN_API_KEY = os.getenv('LANGSMITH_API_KEY')

    # Load the PDF documents from the Healthserve directory.
    loader = PyPDFDirectoryLoader("/Users/clementwong/Documents/GitHub/AIH Project/Healthserve")
    pages = loader.load()

    # Split the documents into smaller chunks.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        length_function=len
    )

    splits = text_splitter.split_documents(pages)

    # Create a vector store to store the embeddings of the document chunks.
    embedding = OpenAIEmbeddings()
    vectordb = Chroma.from_documents(
        documents=splits,
        embedding=embedding,
        persist_directory="./docs/vectordb"
    )

    # Create a memory buffer to store the conversation history.
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        input_key='question',
        output_key='answer'
    )

    # Define dynamic language-specific response templates
    response_templates = {
        "en": """You are Jessie, a support assistant for HealthServe, an IPC registered charity dedicated to bringing healing and hope to the migrant community in Singapore. Your purpose is to support volunteers to improve their understanding of HealthServe in order to enhance their volunteering onboarding process.

            Question: {question}
            Context: {context}

            Please provide me a response that is welcoming and informative at the same time. Please provide brief, to-the-point answers. If necessary, you can summarize your responses in 3-5 sentences.
        """,

        "bn": """আপনি জেসি, HealthServe-এর একজন সহায়ক সহকারী, একটি IPC নিবন্ধিত দাতব্য সংস্থা সিঙ্গাপুরের অভিবাসী সম্প্রদায়ের জন্য নিরাময় এবং আশা নিয়ে আসার জন্য নিবেদিত। আপনার উদ্দেশ্য হল স্বেচ্ছাসেবকদের হেলথ সার্ভ সম্পর্কে তাদের বোঝাপড়ার উন্নতি করতে সহায়তা করা যাতে তাদের স্বেচ্ছাসেবী অনবোর্ডিং প্রক্রিয়া উন্নত করা যায়।

            প্রশ্ন: {question}
            প্রসঙ্গ: {context}

            অনুগ্রহ করে আমাকে একটি প্রতিক্রিয়া প্রদান করুন যা একই সাথে স্বাগত এবং তথ্যপূর্ণ।. আপনার প্রতিক্রিয়া সংক্ষিপ্ত রাখুন।
        """,

        "ta": """நீங்கள் ஜெஸ்ஸி, ஹெல்த்சர்வ் உதவி உதவியாளர் தன்னார்வத் தொண்டர்கள் தங்களுடைய தன்னார்வ ஆன்போர்டிங் செயல்முறையை மேம்படுத்த ஹெல்த்சர்வ் பற்றிய புரிதலை மேம்படுத்த உதவுவதே உங்கள் நோக்கம்.

            கேள்வி: {question}
            சூழல்: {context}

            அதே நேரத்தில் வரவேற்கத்தக்க மற்றும் தகவலறிந்த பதிலை எனக்கு வழங்கவும். உங்கள் பதிலை சுருக்கமாக வைத்திருங்கள்.
        """,

        "zh": """你是 Jessie，HealthServe 的支持助理，HealthServe 是一家 IPC 注册慈善机构，致力于为新加坡的移民社区带来治愈和希望。您的目的是支持志愿者提高对 HealthServe 的了解，以加强他们的志愿服务入职流程。

            问题：{question}
            背景：{context}

            请给我一个热情且内容丰富的回复. 保持你的回答简洁。
        """
    }


    # Select the response template based on the detected language
    response_template = response_templates.get(detected_language, "Language not supported.")
    print(response_template)

    # Create a ConversationalRetrievalChain object.
    qa = ConversationalRetrievalChain.from_llm(
        ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.1),
        combine_docs_chain_kwargs={"prompt": PromptTemplate.from_template(response_template)},
    
    retriever=vectordb.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": .7, "k": 3}),
        return_source_documents=True,
        return_generated_question=True,
        memory=memory
    )
    
    # Generate a response to the given question.
    result = qa({"question": question})
    
    # # Generate the response by replacing placeholders in the template
    # response = response_template.format(question=question, context=context)

    return result['answer']