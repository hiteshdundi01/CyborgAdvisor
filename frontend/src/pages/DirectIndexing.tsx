import { useState } from 'react'
import { motion } from 'framer-motion'
import {
    TrendingUp, Sliders, Shield, Leaf, Play,
    CheckCircle, XCircle, PieChart, BarChart3,
    Plus, Minus, AlertTriangle
} from 'lucide-react'

interface FactorTilt {
    id: string
    name: string
    description: string
    weight: number
}

interface ExclusionCategory {
    id: string
    name: string
    enabled: boolean
    count: number
}

interface IndexHolding {
    ticker: string
    name: string
    weight: number
    sector: string
}

// Available factors
const FACTORS: FactorTilt[] = [
    { id: 'value', name: 'Value', description: 'Low P/E, P/B stocks', weight: 0 },
    { id: 'growth', name: 'Growth', description: 'High earnings growth', weight: 0 },
    { id: 'dividend', name: 'Dividend', description: 'High dividend yield', weight: 0 },
    { id: 'momentum', name: 'Momentum', description: 'Price momentum', weight: 0 },
    { id: 'quality', name: 'Quality', description: 'High ROE, low debt', weight: 0 },
]

// ESG exclusions
const ESG_CATEGORIES: ExclusionCategory[] = [
    { id: 'tobacco', name: 'Tobacco', enabled: false, count: 4 },
    { id: 'defense', name: 'Defense/Weapons', enabled: false, count: 5 },
    { id: 'fossil_fuels', name: 'Fossil Fuels', enabled: false, count: 6 },
    { id: 'gambling', name: 'Gambling', enabled: false, count: 4 },
]

// Mock constructed portfolio
const MOCK_HOLDINGS: IndexHolding[] = [
    { ticker: 'MSFT', name: 'Microsoft', weight: 0.082, sector: 'Technology' },
    { ticker: 'AAPL', name: 'Apple', weight: 0.075, sector: 'Technology' },
    { ticker: 'GOOGL', name: 'Alphabet', weight: 0.048, sector: 'Technology' },
    { ticker: 'JPM', name: 'JPMorgan', weight: 0.032, sector: 'Financials' },
    { ticker: 'JNJ', name: 'Johnson & Johnson', weight: 0.028, sector: 'Healthcare' },
    { ticker: 'PG', name: 'Procter & Gamble', weight: 0.025, sector: 'Consumer Staples' },
    { ticker: 'V', name: 'Visa', weight: 0.022, sector: 'Financials' },
    { ticker: 'HD', name: 'Home Depot', weight: 0.020, sector: 'Consumer Discretionary' },
]

export default function DirectIndexing() {
    const [factors, setFactors] = useState(FACTORS)
    const [exclusions, setExclusions] = useState(ESG_CATEGORIES)
    const [indexName, setIndexName] = useState('My Custom Index')
    const [investmentAmount, setInvestmentAmount] = useState(100000)
    const [isConstructing, setIsConstructing] = useState(false)
    const [portfolio, setPortfolio] = useState<IndexHolding[] | null>(null)
    const [activeTab, setActiveTab] = useState<'builder' | 'portfolio'>('builder')

    const handleFactorChange = (factorId: string, newWeight: number) => {
        setFactors(factors.map(f =>
            f.id === factorId ? { ...f, weight: newWeight } : f
        ))
    }

    const handleExclusionToggle = (categoryId: string) => {
        setExclusions(exclusions.map(e =>
            e.id === categoryId ? { ...e, enabled: !e.enabled } : e
        ))
    }

    const handleConstruct = async () => {
        setIsConstructing(true)
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1500))
        setPortfolio(MOCK_HOLDINGS)
        setIsConstructing(false)
        setActiveTab('portfolio')
    }

    const activeFactors = factors.filter(f => f.weight !== 0)
    const activeExclusions = exclusions.filter(e => e.enabled)
    const totalExcluded = activeExclusions.reduce((sum, e) => sum + e.count, 0)

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-1">Direct Indexing</h1>
                    <p className="text-slate-400">Build hyper-personalized portfolios with tax-lot optimization.</p>
                </div>
                <button
                    onClick={handleConstruct}
                    disabled={isConstructing}
                    className="px-6 py-3 rounded-xl font-semibold bg-gradient-to-r from-cyan-500 to-violet-500 text-white hover:opacity-90 transition-all flex items-center gap-2 disabled:opacity-50"
                >
                    {isConstructing ? (
                        <>
                            <motion.div
                                animate={{ rotate: 360 }}
                                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                            >
                                <PieChart className="w-5 h-5" />
                            </motion.div>
                            Constructing...
                        </>
                    ) : (
                        <>
                            <Play className="w-5 h-5" />
                            Construct Portfolio
                        </>
                    )}
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <Sliders className="w-5 h-5 text-cyan-400" />
                        <span className="text-slate-400 text-sm">Active Tilts</span>
                    </div>
                    <p className="text-2xl font-bold text-white">{activeFactors.length}</p>
                </motion.div>

                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <Leaf className="w-5 h-5 text-emerald-400" />
                        <span className="text-slate-400 text-sm">ESG Exclusions</span>
                    </div>
                    <p className="text-2xl font-bold text-emerald-400">{activeExclusions.length}</p>
                </motion.div>

                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <XCircle className="w-5 h-5 text-amber-400" />
                        <span className="text-slate-400 text-sm">Stocks Excluded</span>
                    </div>
                    <p className="text-2xl font-bold text-amber-400">{totalExcluded}</p>
                </motion.div>

                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <TrendingUp className="w-5 h-5 text-violet-400" />
                        <span className="text-slate-400 text-sm">Investment</span>
                    </div>
                    <p className="text-2xl font-bold text-violet-400">${(investmentAmount / 1000).toFixed(0)}K</p>
                </motion.div>
            </div>

            {/* Tab Navigation */}
            <div className="flex gap-2 border-b border-white/10 pb-2">
                <button
                    onClick={() => setActiveTab('builder')}
                    className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-all ${activeTab === 'builder'
                            ? 'bg-cyan-500/20 text-cyan-400 border-b-2 border-cyan-400'
                            : 'text-slate-400 hover:text-white'
                        }`}
                >
                    Index Builder
                </button>
                <button
                    onClick={() => setActiveTab('portfolio')}
                    className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-all ${activeTab === 'portfolio'
                            ? 'bg-cyan-500/20 text-cyan-400 border-b-2 border-cyan-400'
                            : 'text-slate-400 hover:text-white'
                        }`}
                >
                    Constructed Portfolio
                </button>
            </div>

            {activeTab === 'builder' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Index Configuration */}
                    <motion.div
                        className="glass-card"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                    >
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Sliders className="w-5 h-5 text-cyan-400" />
                            Index Configuration
                        </h3>

                        {/* Index Name */}
                        <div className="mb-6">
                            <label className="block text-sm text-slate-400 mb-2">Index Name</label>
                            <input
                                type="text"
                                value={indexName}
                                onChange={(e) => setIndexName(e.target.value)}
                                className="w-full bg-slate-800/50 border border-white/10 rounded-xl px-4 py-2 text-white focus:border-cyan-500 outline-none"
                            />
                        </div>

                        {/* Investment Amount */}
                        <div className="mb-6">
                            <label className="block text-sm text-slate-400 mb-2">Investment Amount</label>
                            <input
                                type="number"
                                value={investmentAmount}
                                onChange={(e) => setInvestmentAmount(Number(e.target.value))}
                                className="w-full bg-slate-800/50 border border-white/10 rounded-xl px-4 py-2 text-white focus:border-cyan-500 outline-none"
                            />
                        </div>

                        {/* Factor Tilts */}
                        <div className="mb-6">
                            <label className="block text-sm text-slate-400 mb-4">Factor Tilts</label>
                            <div className="space-y-4">
                                {factors.map((factor) => (
                                    <div key={factor.id}>
                                        <div className="flex items-center justify-between mb-1">
                                            <div>
                                                <span className="text-white text-sm">{factor.name}</span>
                                                <span className="text-slate-500 text-xs ml-2">{factor.description}</span>
                                            </div>
                                            <span className={`text-sm font-mono ${factor.weight > 0 ? 'text-emerald-400' :
                                                    factor.weight < 0 ? 'text-rose-400' : 'text-slate-400'
                                                }`}>
                                                {factor.weight > 0 ? '+' : ''}{(factor.weight * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => handleFactorChange(factor.id, Math.max(-1, factor.weight - 0.1))}
                                                className="p-1 rounded bg-slate-700 hover:bg-slate-600"
                                            >
                                                <Minus className="w-4 h-4 text-slate-400" />
                                            </button>
                                            <input
                                                type="range"
                                                min="-100"
                                                max="100"
                                                value={factor.weight * 100}
                                                onChange={(e) => handleFactorChange(factor.id, Number(e.target.value) / 100)}
                                                className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                                            />
                                            <button
                                                onClick={() => handleFactorChange(factor.id, Math.min(1, factor.weight + 0.1))}
                                                className="p-1 rounded bg-slate-700 hover:bg-slate-600"
                                            >
                                                <Plus className="w-4 h-4 text-slate-400" />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </motion.div>

                    {/* ESG Exclusions */}
                    <motion.div
                        className="glass-card"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                    >
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Leaf className="w-5 h-5 text-emerald-400" />
                            ESG/SRI Exclusions
                        </h3>

                        <p className="text-sm text-slate-400 mb-4">
                            Exclude companies based on your values. These companies will be
                            removed from your custom index.
                        </p>

                        <div className="space-y-3">
                            {exclusions.map((category) => (
                                <div
                                    key={category.id}
                                    onClick={() => handleExclusionToggle(category.id)}
                                    className={`p-4 rounded-xl cursor-pointer transition-all border ${category.enabled
                                            ? 'bg-emerald-500/10 border-emerald-500/30'
                                            : 'bg-slate-800/30 border-white/5 hover:bg-slate-800/50'
                                        }`}
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center ${category.enabled
                                                    ? 'bg-emerald-500 border-emerald-500'
                                                    : 'border-slate-500'
                                                }`}>
                                                {category.enabled && <CheckCircle className="w-4 h-4 text-white" />}
                                            </div>
                                            <span className="text-white">{category.name}</span>
                                        </div>
                                        <span className="text-sm text-slate-400">{category.count} stocks</span>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {activeExclusions.length > 0 && (
                            <div className="mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30">
                                <div className="flex items-start gap-2">
                                    <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5" />
                                    <div>
                                        <p className="text-sm text-amber-300">Tracking Error Impact</p>
                                        <p className="text-xs text-slate-400 mt-1">
                                            Excluding {totalExcluded} stocks will increase tracking error by approximately
                                            {(totalExcluded * 0.2).toFixed(1)}% vs benchmark.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Tax Optimization */}
                        <div className="mt-6 p-4 rounded-xl bg-gradient-to-r from-cyan-500/10 to-violet-500/10 border border-cyan-500/20">
                            <div className="flex items-center gap-3 mb-2">
                                <Shield className="w-5 h-5 text-cyan-400" />
                                <span className="text-white font-medium">Tax-Lot Optimization</span>
                            </div>
                            <p className="text-sm text-slate-400">
                                Automatically integrates with Tax-Loss Harvesting to maximize
                                after-tax returns. Rebalancing trades are optimized for tax efficiency.
                            </p>
                        </div>
                    </motion.div>
                </div>
            )}

            {activeTab === 'portfolio' && (
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    {portfolio ? (
                        <>
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                                    <BarChart3 className="w-5 h-5 text-cyan-400" />
                                    {indexName}
                                </h3>
                                <div className="flex gap-4 text-sm">
                                    <div>
                                        <span className="text-slate-400">Holdings:</span>
                                        <span className="text-white ml-2">{portfolio.length}</span>
                                    </div>
                                    <div>
                                        <span className="text-slate-400">Tracking Error:</span>
                                        <span className="text-cyan-400 ml-2">2.1%</span>
                                    </div>
                                    <div>
                                        <span className="text-slate-400">Tax Efficiency:</span>
                                        <span className="text-emerald-400 ml-2">92%</span>
                                    </div>
                                </div>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="text-left text-slate-400 text-sm border-b border-white/10">
                                            <th className="pb-3">Ticker</th>
                                            <th className="pb-3">Name</th>
                                            <th className="pb-3">Sector</th>
                                            <th className="pb-3 text-right">Weight</th>
                                            <th className="pb-3 text-right">Value</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {portfolio.map((holding) => (
                                            <tr key={holding.ticker} className="text-sm hover:bg-white/5">
                                                <td className="py-3 font-mono text-cyan-400">{holding.ticker}</td>
                                                <td className="py-3 text-white">{holding.name}</td>
                                                <td className="py-3 text-slate-400">{holding.sector}</td>
                                                <td className="py-3 text-right text-white">{(holding.weight * 100).toFixed(2)}%</td>
                                                <td className="py-3 text-right text-emerald-400">
                                                    ${(holding.weight * investmentAmount).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* Factor Exposures */}
                            <div className="mt-6 pt-6 border-t border-white/10">
                                <h4 className="text-sm text-slate-400 mb-3">Factor Exposures</h4>
                                <div className="grid grid-cols-5 gap-4">
                                    {factors.map((factor) => (
                                        <div key={factor.id} className="text-center">
                                            <p className="text-xs text-slate-500 mb-1">{factor.name}</p>
                                            <p className={`text-lg font-bold ${factor.weight > 0 ? 'text-emerald-400' :
                                                    factor.weight < 0 ? 'text-rose-400' : 'text-slate-400'
                                                }`}>
                                                {factor.weight > 0 ? '+' : ''}{(factor.weight * 100).toFixed(0)}%
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="text-center py-12 text-slate-400">
                            <PieChart className="w-12 h-12 mx-auto mb-3 opacity-50" />
                            <p>Configure your index and click "Construct Portfolio" to see results</p>
                        </div>
                    )}
                </motion.div>
            )}
        </div>
    )
}
