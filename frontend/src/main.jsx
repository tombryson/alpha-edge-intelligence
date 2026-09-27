import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import ApiAccessGate from './components/ApiAccessGate.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ApiAccessGate><App /></ApiAccessGate>
  </StrictMode>,
)
