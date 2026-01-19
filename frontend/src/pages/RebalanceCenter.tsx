import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, CheckCircle, XCircle, AlertTriangle, Play, Lock } from 'lucide-react'

interface SagaStep {
    name: string
    status: 'pending' | 'running' | 'success' | 'failed' | 'compensated'
    isPivot?: boolean
}

const initialSteps: SagaStep[] = [
    { name: 'ValidateMarket', status: 'pending' },
    { name: 'PlaceSellOrders', status: 'pending' },
    { name: 'SettleCash', status: 'pending' },
    { name: 'PlaceBuyOrders', status: 'pending', isPivot: true },
]

interface Allocation {
    name: string
    current: number
    target: number
}

const initialAllocations: Allocation[] = [
    { name: 'Stocks', current: 60, target: 60 },
    { name: 'Bonds', current: 30, target: 30 },
    { name: 'Cash', current: 8, target: 5 },
    { name: 'Alternatives', current: 2, target: 5 },
]

export default function RebalanceCenter() {
    const [allocations, setAllocations] = useState(initialAllocations)
    const [steps, setSteps] = useState<SagaStep[]>(initialSteps)
    const [isExecuting, setIsExecuting] = useState(false)
    const [showApproval, setShowApproval] = useState(false)

    const updateTarget = (name: string, value: number) => {
        setAllocations(allocations.map(a =>
            a.name === name ? { ...a, target: value } : a
        ))
    }

    const totalTarget = allocations.reduce((sum, a) => sum + a.target, 0)
    const isBalanced = totalTarget === 100

    const calculateTrades = () => {
        // Calculate differences
        const trades = allocations
            .filter(a => Math.abs(a.current - a.target) > 0.5)
            .map(a => ({
                asset: a.name,
                action: a.current > a.target ? 'SELL' : 'BUY',
                amount: Math.abs(a.current - a.target) * 1000, // Mock calculation
                from: a.current,
                to: a.target,
            }))
        return trades
    }

    const trades = calculateTrades()

    const executeSaga = async () => {
        setShowApproval(false)
        setIsExecuting(true)
        setSteps(initialSteps)

        // Simulate saga execution
        for (let i = 0; i < initialSteps.length; i++) {
            // Update to running
            setSteps(prev => prev.map((s, idx) =>
                idx === i ? { ...s, status: 'running' } : s
            ))

            await new Promise(r => setTimeout(r, 1500))

            // Update to success
            setSteps(prev => prev.map((s, idx) =>
                idx === i ? { ...s, status: 'success' } : s
            ))
        }

        setIsExecuting(false)

        // Update allocations to match targets
        setAllocations(allocations.map(a => ({ ...a, current: a.target })))
    }

    const getStepIcon = (status: string) => {
        switch (status) {
            case 'success': return <CheckCircle className="w-5 h-5 text-emerald-400" />
            case 'failed': return <XCircle className="w-5 h-5 text-rose-400" />
            case 'running': return <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin" />
            case 'compensated': return <AlertTriangle className="w-5 h-5 text-amber-400" />
            default: return <div className="w-5 h-5 rounded-full border-2 border-slate-500" />
        }
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-1">Rebalance Center</h1>
                    <p className="text-slate-400">Adjust your target allocation and execute rebalancing.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Target Allocation */}
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                >
                    <h3 className="text-lg font-semibold text-white mb-6">Target Allocation</h3>

                    <div className="space-y-6">
                        {allocations.map((allocation) => (
                            <div key={allocation.name} className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-300">{allocation.name}</span>
                                    <span className="text-white font-medium">{allocation.target}%</span>
                                </div>
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={allocation.target}
                                    onChange={(e) => updateTarget(allocation.name, Number(e.target.value))}
                                    className="w-full"
                                    disabled={isExecuting}
                                />
                                <div className="flex justify-between text-xs text-slate-500">
                                    <span>Current: {allocation.current}%</span>
                                    <span className={allocation.current !== allocation.target ? 'text-cyan-400' : ''}>
                                        {allocation.current !== allocation.target
                                            ? `Δ ${(allocation.target - allocation.current).toFixed(1)}%`
                                            : 'Balanced'}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Total indicator */}
                    <div className={`mt-6 p-3 rounded-xl ${isBalanced ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-rose-500/10 border border-rose-500/30'}`}>
                        <div className="flex justify-between items-center">
                            <span className="text-sm">Total Allocation</span>
                            <span className={`font-bold ${isBalanced ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {totalTarget}%
                            </span>
                        </div>
                        {!isBalanced && (
                            <p className="text-xs text-rose-400 mt-1">Must equal 100%</p>
                        )}
                    </div>
                </motion.div>

                {/* Proposed Trades */}
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                >
                    <h3 className="text-lg font-semibold text-white mb-6">Proposed Trades</h3>

                    {trades.length === 0 ? (
                        <div className="text-center py-8 text-slate-400">
                            <CheckCircle className="w-12 h-12 mx-auto mb-3 text-emerald-400" />
                            <p>Portfolio is balanced. No trades needed.</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {trades.map((trade, idx) => (
                                <motion.div
                                    key={trade.asset}
                                    className={`p-4 rounded-xl ${trade.action === 'BUY' ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-rose-500/10 border border-rose-500/30'}`}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.1 }}
                                >
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <span className={`font-bold ${trade.action === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}`}>
                                                {trade.action}
                                            </span>
                                            <span className="text-white ml-2">{trade.asset}</span>
                                        </div>
                                        <span className="text-white font-medium">${trade.amount.toLocaleString()}</span>
                                    </div>
                                    <p className="text-xs text-slate-400 mt-1">
                                        {trade.from}% → {trade.to}%
                                    </p>
                                </motion.div>
                            ))}
                        </div>
                    )}

                    {/* Execute Button */}
                    {trades.length > 0 && isBalanced && (
                        <button
                            onClick={() => setShowApproval(true)}
                            disabled={isExecuting}
                            className="btn-primary w-full mt-6 flex items-center justify-center gap-2"
                        >
                            <Play className="w-4 h-4" />
                            {isExecuting ? 'Executing...' : 'Execute Rebalance'}
                        </button>
                    )}
                </motion.div>
            </div>

            {/* Saga Execution Visualization */}
            {isExecuting || steps.some(s => s.status !== 'pending') ? (
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <h3 className="text-lg font-semibold text-white mb-4">Saga Execution</h3>
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
                            <h3 className="text-xl font-bold text-white mb-4">Confirm Rebalance</h3>
                            <p className="text-slate-400 mb-6">
                                This will execute {trades.length} trades. Once past the pivot transaction,
                                changes cannot be automatically reversed.
                            </p>

                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowApproval(false)}
                                    className="btn-danger flex-1"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={executeSaga}
                                    className="btn-success flex-1"
                                >
                                    Approve & Execute
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}
