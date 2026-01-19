import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import PortfolioManager from './pages/PortfolioManager'
import RebalanceCenter from './pages/RebalanceCenter'
import TaxLossHarvesting from './pages/TaxLossHarvesting'
import SagaMonitor from './pages/SagaMonitor'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="portfolio" element={<PortfolioManager />} />
            <Route path="rebalance" element={<RebalanceCenter />} />
            <Route path="tax-loss-harvesting" element={<TaxLossHarvesting />} />
            <Route path="saga-monitor" element={<SagaMonitor />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
