# Vietnamese Legal RAG

A web application for Vietnamese legal document retrieval and question answering using React frontend and Python RAG backend.

## Project Structure

Frontend: React 18 with Vite, Zustand state management, and Axios HTTP client
Backend: FastAPI with LangChain RAG, Chroma vector store, and LLM integration

## Quick Start

Frontend:
```bash
cd frontend
npm install
npm run dev
```
Access at http://localhost:3000

Backend:
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```
Access at http://localhost:8000

## Features

Frontend: ChatGPT-like interface, conversation history, source citations, responsive design
Backend: RAG pipeline, document retrieval, LLM generation, configurable parameters

## Configuration

Backend: Edit .env with OpenAI API key and settings
Frontend: Edit .env with API endpoint

## API Endpoints

GET / - Root endpoint
GET /api/health - Health check
POST /api/query - Query the RAG system
POST /api/documents/add - Add document to knowledge base

