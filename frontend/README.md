# Vietnamese Legal RAG - Frontend

A modern React application with a ChatGPT-like interface for legal question answering.

## Features

- 💬 ChatGPT-like conversation interface
- 📚 Source document citations
- 💾 Conversation history management
- 📱 Responsive design
- ✨ Markdown support for formatted answers
- ⚡ Real-time message updates

## Tech Stack

- **React 18** - UI library
- **Vite** - Build tool
- **Zustand** - State management
- **Axios** - HTTP client
- **React Markdown** - Markdown rendering
- **CSS3** - Modern styling

## Project Structure

```
src/
├── components/        # React components
│   ├── ChatWindow.jsx    # Message display
│   ├── InputArea.jsx     # Message input
│   ├── MessageItem.jsx   # Single message
│   └── Sidebar.jsx       # Conversation list
├── pages/            # Page components
│   └── ChatPage.jsx   # Main chat page
├── services/         # API integration
│   └── api.js        # API client
├── store/            # State management
│   └── chatStore.js  # Zustand store
├── styles/           # CSS files
├── utils/            # Utility functions
├── App.jsx           # Root component
└── main.jsx          # Entry point
```

## Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

1. Install dependencies
```bash
npm install
```

2. Create `.env` file (copy from `.env.example`)
```bash
cp .env.example .env
```

3. Update API endpoint in `.env`
```env
REACT_APP_API_URL=http://localhost:8000/api
```

### Running Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Available Scripts

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

## Component Overview

### ChatPage
Main page component that manages:
- Conversations list
- Current conversation selection
- Sidebar toggle
- Message display and input

### ChatWindow
Displays messages in a scrollable container with:
- User and assistant message styling
- Markdown rendering
- Source document display
- Auto-scroll to latest message

### InputArea
Message input component with:
- Textarea for multi-line input
- Send button with loading state
- Enter key shortcut (Shift+Enter for newline)
- Disabled state during message processing

### Sidebar
Conversation management with:
- List of conversations
- Current conversation highlight
- Delete conversation button
- New chat button

### MessageItem
Individual message component with:
- Role-based styling (user vs assistant)
- Markdown content rendering
- Source citations
- Avatar icons

## API Integration

The frontend communicates with the backend via:

```javascript
// Query endpoint
POST /api/query
Request: { query, conversation_id?, top_k? }
Response: { query, answer, sources, processing_time, model_used }

// Health check
GET /api/health
Response: { status, version, llm_configured, vector_store_ready }
```

## Styling

Custom CSS provides:
- ChatGPT-inspired color scheme (purple gradient buttons)
- Responsive layout
- Smooth animations
- Modern shadows and borders

Color scheme:
- Primary: `#4f46e5` - `#7c3aed` (indigo to violet gradient)
- Background: `#ffffff` to `#f5f5f5`
- Borders: `#e0e0e0`
- Text: `#333333` / `#666666`

## State Management (Zustand)

Store provides:
- Conversations list
- Current conversation
- Add/delete conversation methods
- Add message to conversation
- Set current conversation

## Customization

### Change Theme Colors
Edit `src/styles/*.css` and update color values:
- `.message-item.user .message-content`: User message background
- `.message-item.assistant .message-content`: Assistant message background
- `.send-btn`: Send button styling
- `.new-chat-btn`: New chat button styling

### Modify API Endpoint
Update `REACT_APP_API_URL` in `.env`

### Add New Components
1. Create component in `src/components/`
2. Import and use in pages
3. Add corresponding CSS in `src/styles/`

## Performance Optimization

- Code splitting via Vite
- Lazy loading of conversations
- Memoized component rendering
- Virtual scrolling for long message lists (optional)

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Troubleshooting

### API Connection Issues
- Check `REACT_APP_API_URL` is correct
- Ensure backend is running on port 8000
- Check browser console for CORS errors

### Messages Not Sending
- Verify backend is responding at `/api/health`
- Check network tab in browser DevTools
- Ensure OpenAI API key is configured on backend

### Styling Issues
- Clear browser cache
- Check CSS files are imported correctly
- Verify Tailwind/CSS classes are in scope

## Deployment

### Build for Production
```bash
npm run build
```

### Deploy to Vercel
```bash
vercel deploy
```

### Deploy to Netlify
```bash
npm run build
# Drag and drop dist/ folder to Netlify
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REACT_APP_API_URL` | Backend API endpoint | `http://localhost:8000/api` |

## License

MIT

## Support

For issues and feature requests, please open an issue on the project repository.
