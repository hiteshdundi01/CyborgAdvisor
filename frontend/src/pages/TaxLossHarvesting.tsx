import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { TrendingDown, AlertTriangle, DollarSign, Calendar, RefreshCw, CheckCircle, Lock, Play } from 'lucide-react'

interface LossOpportunity {
    lotId: string
    asset: string
    loss: number
    holdingPeriod: 'short_term' | 'long_term'
    daysHeld: number
    washSaleClear: boolean
    replacement?: string
}

const mockOpportunities: LossOpportunity[] = [
    { lotId: 'LOT_001', asset: 'NVDA', loss: 2100, holdingPeriod: 'short_term', daysHeld: 60, washSaleClear: true, replacement: 'AMD' },
    { lotId: 'LOT_002', asset: 'VTI', loss: 1650, holdingPeriod: 'long_term', daysHeld: 400, washSaleClear: false },
    { lotId: 'LOT_003', asset: 'AAPL', loss: 1395, holdingPeriod: 'short_term', daysHeld: 45, washSaleClear: true },
    { lotId: 'LOT_004', asset: 'BND', loss: 1100, holdingPeriod: 'long_term', daysHeld: 500, washSaleClear: true, replacement: 'AGG' },
    { lotId: 'LOT_005', asset: 'MSFT', loss: 862, holdingPeriod: 'short_term', daysHeld: 200, washSaleClear: true },
    { lotId: 'LOT_006', asset: 'VOO', loss: 625, holdingPeriod: 'long_term', daysHeld: 450, washSaleClear: true, replacement: 'SPY' },
]

interface SagaStep {
    name: string
    status: 'pending' | 'running' | 'success' | 'failed' | 'compensated'
    isPivot?: boolean
}

const tlhSteps: SagaStep[] = [
    { name: 'IdentifyLosses', status: 'pending' },
    { name: 'CheckWashSale', status: 'pending' },
    { name: 'SellLossPositions', status: 'pending' },
    { name: 'PurchaseReplacement', status: 'pending', isPivot: true },
    { name: 'RecordTaxLot', status: 'pending' },
]

export default function TaxLossHarvesting() {
    const [opportunities] = useState<LossOpportunity[]>(mockOpportunities)
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
    const [steps, setSteps] = useState<SagaStep[]>(tlhSteps)
    const [isExecuting, setIsExecuting] = useState(false)
    const [showApproval, setShowApproval] = useState(false)

    const validOpportunities = opportunities.filter(o => o.washSaleClear)
    const totalLoss = Array.from(selectedIds)
        .map(id => opportunities.find(o => o.lotId === id)?.loss || 0)
        .reduce((sum, loss) => sum + loss, 0)

    // Tax savings calculation (24% federal + 5% state for short-term, 15% for long-term)
    const calculateSavings = () => {
        let savings = 0
        Array.from(selectedIds).forEach(id => {
            const opp = opportunities.find(o => o.lotId === id)
            if (opp) {
                savings += opp.holdingPeriod === 'short_term'
                    ? opp.loss * 0.29
                    : opp.loss * 0.15
            }
        })
        return savings
    }

    const toggleSelection = (lotId: string) => {
        const opp = opportunities.find(o => o.lotId === lotId)
        if (opp && opp.washSaleClear) {
            const newSelected = new Set(selectedIds)
            if (newSelected.has(lotId)) {
                newSelected.delete(lotId)
            } else {
                newSelected.add(lotId)
            }
            setSelectedIds(newSelected)
        }
    }

    const selectAll = () => {
        setSelectedIds(new Set(validOpportunities.map(o => o.lotId)))
    }

    const executeTLH = async () => {
        setShowApproval(false)
        setIsExecuting(true)
        setSteps(tlhSteps)

        for (let i = 0; i < tlhSteps.length; i++) {
            setSteps(prev => prev.map((s, idx) =>
                idx === i ? { ...s, status: 'running' } : s
            ))

            await new Promise(r => setTimeout(r, 1200))

            setSteps(prev => prev.map((s, idx) =>
                idx === i ? { ...s, status: 'success' } : s
            ))
        }

        setIsExecuting(false)
    }

    const getStepIcon = (status: string) => {
        switch (status) {
            case 'success': return <CheckCircle className="w-5 h-5 text-emerald-400" />
            case 'failed': return <AlertTriangle className="w-5 h-5 text-rose-400" />
            case 'running': return <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin" />
            default: return <div className="w-5 h-5 rounded-full border-2 border-slate-500" />
        }
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-1">Tax Loss Harvesting</h1>
                    <p className="text-slate-400">Identify and harvest losses to optimize your tax liability.</p>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-xl bg-rose-500/20 flex items-center justify-center">
                            <TrendingDown className="w-5 h-5 text-rose-400" />
                        </div>
                        <span className="text-slate-400 text-sm">Selected Losses</span>
                    </div>
                    <p className="text-2xl font-bold text-white">${totalLoss.toLocaleString()}</p>
                </motion.div>

                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                >
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                            <DollarSign className="w-5 h-5 text-emerald-400" />
                        </div>
                        <span className="text-slate-400 text-sm">Est. Tax Savings</span>
                    </div>
                    <p className="text-2xl font-bold text-emerald-400">${calculateSavings().toLocaleString()}</p>
                </motion.div>

                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                            <AlertTriangle className="w-5 h-5 text-amber-400" />
                        </div>
                        <span className="text-slate-400 text-sm">Wash Sale Blocked</span>
                    </div>
                    <p className="text-2xl font-bold text-amber-400">
                        {opportunities.filter(o => !o.washSaleClear).length}
                    </p>
                </motion.div>

                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                >
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center">
                            <Calendar className="w-5 h-5 text-cyan-400" />
                        </div>
                        <span className="text-slate-400 text-sm">Tax Year</span>
                    </div>
                    <p className="text-2xl font-bold text-white">2026</p>
                </motion.div>
            </div>

            {/* Opportunities Table */}
            <motion.div
                className="glass-card p-0 overflow-hidden"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
            >
                <div className="p-4 border-b border-white/10 flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-white">Loss Opportunities</h3>
                    <button onClick={selectAll} className="text-sm text-cyan-400 hover:text-cyan-300">
                        Select All Valid
                    </button>
                </div>

                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Select</th>
                            <th>Asset</th>
                            <th>Loss</th>
                            <th>Holding</th>
                            <th>Days Held</th>
                            <th>Wash Sale</th>
                            <th>Replacement</th>
                        </tr>
                    </thead>
                    <tbody>
                        {opportunities.map((opp) => (
                            <tr
                                key={opp.lotId}
                                className={`cursor-pointer ${!opp.washSaleClear ? 'opacity-50' : ''}`}
                                onClick={() => toggleSelection(opp.lotId)}
                            >
                                <td>
                                    <input
                                        type="checkbox"
                                        checked={selectedIds.has(opp.lotId)}
                                        onChange={() => toggleSelection(opp.lotId)}
                                        disabled={!opp.washSaleClear}
                                        className="w-4 h-4 rounded"
                                    />
                                </td>
                                <td>
                                    <span className="font-medium text-white">{opp.asset}</span>
                                    <p className="text-xs text-slate-500">{opp.lotId}</p>
                                </td>
                                <td>
                                    <span className="text-rose-400 font-medium">-${opp.loss.toLocaleString()}</span>
                                </td>
                                <td>
                                    <span className={`badge ${opp.holdingPeriod === 'short_term' ? 'badge-warning' : 'badge-info'}`}>
                                        {opp.holdingPeriod === 'short_term' ? 'Short' : 'Long'}
                                    </span>
                                </td>
                                <td>
                                    <span className="text-slate-300">{opp.daysHeld} days</span>
                                </td>
                                <td>
                                    {opp.washSaleClear ? (
                                        <span className="badge badge-success">Clear</span>
                                    ) : (
                                        <span className="badge badge-danger">Blocked</span>
                                    )}
                                </td>
                                <td>
                                    {opp.replacement ? (
                                        <span className="text-cyan-400">{opp.replacement}</span>
                                    ) : (
                                        <span className="text-slate-500">—</span>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </motion.div>

            {/* Execute Button */}
            {selectedIds.size > 0 && (
                <div className="flex justify-end">
                    <button
                        onClick={() => setShowApproval(true)}
                        disabled={isExecuting}
                        className="btn-primary flex items-center gap-2"
                    >
                        <Play className="w-4 h-4" />
                        Harvest {selectedIds.size} Position{selectedIds.size > 1 ? 's' : ''}
                    </button>
                </div>
            )}

            {/* Saga Execution */}
            {isExecuting || steps.some(s => s.status !== 'pending') ? (
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <h3 className="text-lg font-semibold text-white mb-4">TLH Saga Execution</h3>
                    <div className="space-y-2">
                        {steps.map((step, idx) => (
                            <motion.div
                                key={step.name}
                                className={`saga-step saga-step-${step.status} ${step.isPivot ? 'saga-step-pivot' : ''}`}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.1 }}
                            >
                                {getStepIcon(step.status)}
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <span className="font-medium text-white">{step.name}</span>
                                        {step.isPivot && (
                                            <span className="badge badge-warning text-xs flex items-center gap-1">
                                                <Lock className="w-3 h-3" />
                                                PIVOT
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-xs text-slate-400 capitalize">{step.status}</p>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>
            ) : null}

            {/* Approval Modal */}
            <AnimatePresence>
                {showApproval && (
                    <motion.div
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setShowApproval(false)}
                    >
                        <motion.div
                            className="glass-card max-w-md mx-4"
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <h3 className="text-xl font-bold text-white mb-4">Confirm Tax Loss Harvest</h3>
                            <div className="space-y-3 mb-6">
                                <div className="flex justify-between">
                                    <span className="text-slate-400">Positions</span>
                                    <span className="text-white">{selectedIds.size}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-400">Total Losses</span>
                                    <span className="text-rose-400">${totalLoss.toLocaleString()}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-400">Est. Tax Savings</span>
                                    <span className="text-emerald-400">${calculateSavings().toLocaleString()}</span>
                                </div>
                            </div>

                            <p className="text-sm text-slate-400 mb-6">
                                Once past the PurchaseReplacement step (PIVOT), changes cannot be automatically reversed.
                            </p>

                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowApproval(false)}
                                    className="btn-danger flex-1"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={executeTLH}
                                    className="btn-success flex-1"
                                >
                                    Harvest Losses
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}
