# Vietnamese Legal RAG - Frontend

React application with a ChatGPT-like interface for legal question answering.

## Features

ChatGPT-like conversation interface, source document citations, conversation history management, responsive design, markdown support for formatted answers.

## Tech Stack

React 18, Vite, Zustand, Axios, React Markdown, CSS3.

## Getting Started

Prerequisites: Node.js 18+, npm or yarn

Installation:
```bash
npm install
cp .env.example .env
npm run dev
```

Access at http://localhost:3000

## Project Structure

src/
- components/: React components (ChatWindow, InputArea, MessageItem, Sidebar)
- pages/: Page components (ChatPage)
- services/: API integration (api.js)
- store/: State management (chatStore.js)
- styles/: CSS files
- App.jsx, main.jsx

## Available Scripts

npm run dev - Start development server
npm run build - Build for production
npm run preview - Preview production build
npm run lint - Run linter

## API Integration

Query endpoint: POST /api/query
Request: { query, conversation_id?, top_k? }
Response: { query, answer, sources, processing_time, model_used }

Health check: GET /api/health

## Environment Variables

VITE_API_URL - Backend API endpoint (default: http://localhost:8000/api)

## Customization

Change theme colors in src/styles/*.css
Modify API endpoint in .env
Add new components in src/components/

## Browser Support

Chrome/Edge, Firefox, Safari, mobile browsers (latest versions)

## License

MIT

