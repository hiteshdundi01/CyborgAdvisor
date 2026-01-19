import { useState } from 'react'
import { motion } from 'framer-motion'
import { Activity, CheckCircle, XCircle, AlertTriangle, RefreshCw, Clock, Lock } from 'lucide-react'

interface SagaExecution {
    id: string
    type: 'rebalance' | 'tlh'
    status: 'success' | 'failed' | 'rolled_back'
    timestamp: string
    stepsCompleted: number
    totalSteps: number
    error?: string
}

const mockExecutions: SagaExecution[] = [
    { id: 'saga_abc123', type: 'rebalance', status: 'success', timestamp: '2026-01-19 10:30:00', stepsCompleted: 4, totalSteps: 4 },
    { id: 'saga_def456', type: 'tlh', status: 'success', timestamp: '2026-01-18 14:15:00', stepsCompleted: 5, totalSteps: 5 },
    { id: 'saga_ghi789', type: 'rebalance', status: 'rolled_back', timestamp: '2026-01-17 09:45:00', stepsCompleted: 2, totalSteps: 4, error: 'Insufficient funds' },
    { id: 'saga_jkl012', type: 'tlh', status: 'success', timestamp: '2026-01-16 16:20:00', stepsCompleted: 5, totalSteps: 5 },
    { id: 'saga_mno345', type: 'rebalance', status: 'success', timestamp: '2026-01-15 11:00:00', stepsCompleted: 4, totalSteps: 4 },
]

const rebalanceSteps = ['ValidateMarket', 'PlaceSellOrders', 'SettleCash', 'PlaceBuyOrders']
const tlhSteps = ['IdentifyLosses', 'CheckWashSale', 'SellLossPositions', 'PurchaseReplacement', 'RecordTaxLot']

export default function SagaMonitor() {
    const [selectedSaga, setSelectedSaga] = useState<SagaExecution | null>(null)
    const [filter, setFilter] = useState<'all' | 'rebalance' | 'tlh'>('all')

    const filteredExecutions = filter === 'all'
        ? mockExecutions
        : mockExecutions.filter(e => e.type === filter)

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'success': return <CheckCircle className="w-5 h-5 text-emerald-400" />
            case 'failed': return <XCircle className="w-5 h-5 text-rose-400" />
            case 'rolled_back': return <AlertTriangle className="w-5 h-5 text-amber-400" />
            default: return <RefreshCw className="w-5 h-5 text-cyan-400" />
        }
    }

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'success': return 'badge-success'
            case 'failed': return 'badge-danger'
            case 'rolled_back': return 'badge-warning'
            default: return 'badge-info'
        }
    }

    const getSteps = (type: string) => type === 'rebalance' ? rebalanceSteps : tlhSteps
    const getPivotIndex = (type: string) => type === 'rebalance' ? 3 : 3

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-1">Saga Monitor</h1>
                    <p className="text-slate-400">Track and audit saga executions with full transaction logs.</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setFilter('all')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${filter === 'all'
                                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                                : 'bg-slate-800/50 text-slate-400 hover:bg-slate-800'
                            }`}
                    >
                        All
                    </button>
                    <button
                        onClick={() => setFilter('rebalance')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${filter === 'rebalance'
                                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                                : 'bg-slate-800/50 text-slate-400 hover:bg-slate-800'
                            }`}
                    >
                        Rebalance
                    </button>
                    <button
                        onClick={() => setFilter('tlh')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${filter === 'tlh'
                                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                                : 'bg-slate-800/50 text-slate-400 hover:bg-slate-800'
                            }`}
                    >
                        Tax Loss Harvest
                    </button>
                </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <Activity className="w-5 h-5 text-cyan-400" />
                        <span className="text-slate-400 text-sm">Total Executions</span>
                    </div>
                    <p className="text-2xl font-bold text-white">{mockExecutions.length}</p>
                </motion.div>

                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <CheckCircle className="w-5 h-5 text-emerald-400" />
                        <span className="text-slate-400 text-sm">Successful</span>
                    </div>
                    <p className="text-2xl font-bold text-emerald-400">
                        {mockExecutions.filter(e => e.status === 'success').length}
                    </p>
                </motion.div>

                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <AlertTriangle className="w-5 h-5 text-amber-400" />
                        <span className="text-slate-400 text-sm">Rolled Back</span>
                    </div>
                    <p className="text-2xl font-bold text-amber-400">
                        {mockExecutions.filter(e => e.status === 'rolled_back').length}
                    </p>
                </motion.div>

                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <Clock className="w-5 h-5 text-violet-400" />
                        <span className="text-slate-400 text-sm">Success Rate</span>
                    </div>
                    <p className="text-2xl font-bold text-white">
                        {Math.round((mockExecutions.filter(e => e.status === 'success').length / mockExecutions.length) * 100)}%
                    </p>
                </motion.div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Execution List */}
                <motion.div
                    className="glass-card p-0 overflow-hidden"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                >
                    <div className="p-4 border-b border-white/10">
                        <h3 className="text-lg font-semibold text-white">Execution History</h3>
                    </div>

                    <div className="divide-y divide-white/5">
                        {filteredExecutions.map((execution) => (
                            <div
                                key={execution.id}
                                onClick={() => setSelectedSaga(execution)}
                                className={`p-4 cursor-pointer transition-all hover:bg-white/5 ${selectedSaga?.id === execution.id ? 'bg-cyan-500/10 border-l-2 border-cyan-400' : ''
                                    }`}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        {getStatusIcon(execution.status)}
                                        <div>
                                            <p className="font-medium text-white capitalize">{execution.type}</p>
                                            <p className="text-xs text-slate-500 font-mono">{execution.id}</p>
                                        </div>
                                    </div>
                                    <span className={`badge ${getStatusBadge(execution.status)}`}>
                                        {execution.status.replace('_', ' ')}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-slate-400">{execution.timestamp}</span>
                                    <span className="text-slate-500">
                                        {execution.stepsCompleted}/{execution.totalSteps} steps
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </motion.div>

                {/* Saga Detail */}
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                >
                    <h3 className="text-lg font-semibold text-white mb-4">Saga Details</h3>

                    {selectedSaga ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-sm text-slate-400">Transaction ID</p>
                                    <p className="font-mono text-cyan-400">{selectedSaga.id}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-slate-400">Type</p>
                                    <p className="text-white capitalize">{selectedSaga.type}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-slate-400">Timestamp</p>
                                    <p className="text-white">{selectedSaga.timestamp}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-slate-400">Status</p>
                                    <span className={`badge ${getStatusBadge(selectedSaga.status)}`}>
                                        {selectedSaga.status.replace('_', ' ')}
                                    </span>
                                </div>
                            </div>

                            {selectedSaga.error && (
                                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30">
                                    <p className="text-sm text-rose-400">{selectedSaga.error}</p>
                                </div>
                            )}

                            <div className="border-t border-white/10 pt-4">
                                <h4 className="text-sm font-medium text-white mb-3">Step Execution</h4>
                                <div className="space-y-2">
                                    {getSteps(selectedSaga.type).map((step, idx) => {
                                        const isCompleted = idx < selectedSaga.stepsCompleted
                                        const isFailed = idx === selectedSaga.stepsCompleted && selectedSaga.status !== 'success'
                                        const isPivot = idx === getPivotIndex(selectedSaga.type)

                                        return (
                                            <div
                                                key={step}
                                                className={`saga-step ${isCompleted ? 'saga-step-success' :
                                                        isFailed ? 'saga-step-failed' : 'saga-step-pending'
                                                    } ${isPivot ? 'saga-step-pivot' : ''}`}
                                            >
                                                {isCompleted && <CheckCircle className="w-4 h-4 text-emerald-400" />}
                                                {isFailed && <XCircle className="w-4 h-4 text-rose-400" />}
                                                {!isCompleted && !isFailed && <div className="w-4 h-4 rounded-full border-2 border-slate-500" />}
                                                <div className="flex-1 flex items-center gap-2">
                                                    <span className="text-sm text-white">{step}</span>
                                                    {isPivot && (
                                                        <span className="badge badge-warning text-xs flex items-center gap-1">
                                                            <Lock className="w-3 h-3" />
                                                            PIVOT
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-12 text-slate-400">
                            <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                            <p>Select a saga to view details</p>
                        </div>
                    )}
                </motion.div>
            </div>
        </div>
    )
}
