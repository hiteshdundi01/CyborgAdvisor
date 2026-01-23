import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
    Shield, FileText, Download, Search, Filter,
    CheckCircle, XCircle, AlertTriangle, Eye, Clock,
    User, Bot, Key, ChevronRight
} from 'lucide-react'

interface AuditEvent {
    event_id: string
    timestamp: string
    agent_id: string
    agent_authority: string
    human_supervisor: string
    event_type: string
    saga_transaction_id: string
    step_name: string | null
    action_taken: string
    reasoning_trace: string
    decision_factors: string[]
    validation_results: Array<{
        gate_id: string
        passed: boolean
        reason: string
    }>
}

interface AuditTransaction {
    transaction_id: string
    first_event: string
    last_event: string
    event_count: number
    agent_id: string
    status: string
}

interface Agent {
    agent_id: string
    agent_type: string
    version: string
    authority: string
    owner: string
    description: string
}

// Mock data for demo
const mockTransactions: AuditTransaction[] = [
    { transaction_id: 'saga_abc123', first_event: '2026-01-23T10:30:00', last_event: '2026-01-23T10:30:45', event_count: 8, agent_id: 'agent:tlh_agent:1.0.0', status: 'completed' },
    { transaction_id: 'saga_def456', first_event: '2026-01-22T14:15:00', last_event: '2026-01-22T14:15:30', event_count: 6, agent_id: 'agent:rebalance_agent:1.0.0', status: 'completed' },
    { transaction_id: 'saga_ghi789', first_event: '2026-01-21T09:45:00', last_event: '2026-01-21T09:46:12', event_count: 5, agent_id: 'agent:rebalance_agent:1.0.0', status: 'failed' },
]

const mockEvents: AuditEvent[] = [
    {
        event_id: 'evt_001',
        timestamp: '2026-01-23T10:30:00',
        agent_id: 'agent:tlh_agent:1.0.0',
        agent_authority: 'trade_medium',
        human_supervisor: 'system',
        event_type: 'saga_started',
        saga_transaction_id: 'saga_abc123',
        step_name: null,
        action_taken: 'Initiated Tax Loss Harvesting saga',
        reasoning_trace: 'User requested TLH execution. Validated 28 tax lots for harvesting opportunities.',
        decision_factors: ['28 tax lots analyzed', '5 opportunities identified', 'Total loss: $2,450'],
        validation_results: [
            { gate_id: 'gate_authority', passed: true, reason: 'Agent has TRADE_MEDIUM authority' },
            { gate_id: 'gate_cash_min', passed: true, reason: 'Cash at 5% exceeds 2% minimum' },
        ]
    },
    {
        event_id: 'evt_002',
        timestamp: '2026-01-23T10:30:15',
        agent_id: 'agent:tlh_agent:1.0.0',
        agent_authority: 'trade_medium',
        human_supervisor: 'system',
        event_type: 'step_executed',
        saga_transaction_id: 'saga_abc123',
        step_name: 'IdentifyLosses',
        action_taken: 'Scanned portfolio for loss opportunities using FIFO ordering',
        reasoning_trace: 'Applied FIFO ordering to identify highest priority losses. Filtered positions with unrealized losses > $100 threshold.',
        decision_factors: ['FIFO ordering applied', 'Min threshold: $100', '5 lots qualified'],
        validation_results: []
    },
    {
        event_id: 'evt_003',
        timestamp: '2026-01-23T10:30:25',
        agent_id: 'agent:tlh_agent:1.0.0',
        agent_authority: 'trade_medium',
        human_supervisor: 'system',
        event_type: 'compliance_check',
        saga_transaction_id: 'saga_abc123',
        step_name: 'CheckWashSale',
        action_taken: 'Validated wash sale rules across 30+ fund families',
        reasoning_trace: 'Checked all 5 opportunities against IRS wash sale rule. VTI flagged as substantially identical to VTSAX purchased 15 days ago.',
        decision_factors: ['30+ fund families checked', 'VTI/VTSAX wash sale detected', '4 opportunities remain valid'],
        validation_results: [
            { gate_id: 'gate_wash_sale', passed: false, reason: 'VTI substantially identical to VTSAX (Vanguard Total Stock)' },
        ]
    },
]

const mockAgents: Agent[] = [
    { agent_id: 'agent:tlh_agent:1.0.0:abc123', agent_type: 'TLH_AGENT', version: '1.0.0', authority: 'trade_medium', owner: 'System', description: 'Tax Loss Harvesting Agent' },
    { agent_id: 'agent:rebalance_agent:1.0.0:def456', agent_type: 'REBALANCE_AGENT', version: '1.0.0', authority: 'trade_medium', owner: 'System', description: 'Portfolio Rebalancing Agent' },
    { agent_id: 'agent:analysis_agent:1.0.0:ghi789', agent_type: 'ANALYSIS_AGENT', version: '1.0.0', authority: 'read_only', owner: 'System', description: 'Read-only Analysis Agent' },
]

export default function AuditMonitor() {
    const [selectedTransaction, setSelectedTransaction] = useState<AuditTransaction | null>(null)
    const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null)
    const [activeTab, setActiveTab] = useState<'transactions' | 'agents'>('transactions')
    const [searchTerm, setSearchTerm] = useState('')

    const getEventIcon = (eventType: string) => {
        switch (eventType) {
            case 'saga_started': return <Shield className="w-4 h-4 text-cyan-400" />
            case 'saga_completed': return <CheckCircle className="w-4 h-4 text-emerald-400" />
            case 'step_executed': return <ChevronRight className="w-4 h-4 text-blue-400" />
            case 'compliance_check': return <Eye className="w-4 h-4 text-violet-400" />
            case 'error_occurred': return <XCircle className="w-4 h-4 text-rose-400" />
            case 'validation_gate_passed': return <CheckCircle className="w-4 h-4 text-emerald-400" />
            case 'validation_gate_failed': return <AlertTriangle className="w-4 h-4 text-amber-400" />
            default: return <Clock className="w-4 h-4 text-slate-400" />
        }
    }

    const getAuthorityBadge = (authority: string) => {
        switch (authority) {
            case 'admin': return 'bg-rose-500/20 text-rose-400 border-rose-500/30'
            case 'trade_large': return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
            case 'trade_medium': return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
            case 'trade_small': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
            default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30'
        }
    }

    const handleExport = (format: 'json' | 'csv') => {
        // In production: call export API endpoint
        alert(`Exporting audit trail as ${format.toUpperCase()}...`)
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-1">Audit Monitor</h1>
                    <p className="text-slate-400">SEC/FCA Compliant audit trail with full explainability.</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => handleExport('json')}
                        className="px-4 py-2 rounded-lg text-sm font-medium bg-slate-800/50 text-slate-400 hover:bg-slate-800 transition-all flex items-center gap-2"
                    >
                        <Download className="w-4 h-4" />
                        Export JSON
                    </button>
                    <button
                        onClick={() => handleExport('csv')}
                        className="px-4 py-2 rounded-lg text-sm font-medium bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 transition-all flex items-center gap-2"
                    >
                        <FileText className="w-4 h-4" />
                        Export CSV
                    </button>
                </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <Shield className="w-5 h-5 text-cyan-400" />
                        <span className="text-slate-400 text-sm">Total Audited</span>
                    </div>
                    <p className="text-2xl font-bold text-white">{mockTransactions.length}</p>
                </motion.div>

                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <Bot className="w-5 h-5 text-violet-400" />
                        <span className="text-slate-400 text-sm">Active Agents</span>
                    </div>
                    <p className="text-2xl font-bold text-violet-400">{mockAgents.length}</p>
                </motion.div>

                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <CheckCircle className="w-5 h-5 text-emerald-400" />
                        <span className="text-slate-400 text-sm">Gates Passed</span>
                    </div>
                    <p className="text-2xl font-bold text-emerald-400">247</p>
                </motion.div>

                <motion.div className="glass-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                    <div className="flex items-center gap-3 mb-2">
                        <AlertTriangle className="w-5 h-5 text-amber-400" />
                        <span className="text-slate-400 text-sm">Gates Failed</span>
                    </div>
                    <p className="text-2xl font-bold text-amber-400">3</p>
                </motion.div>
            </div>

            {/* Tab Navigation */}
            <div className="flex gap-2 border-b border-white/10 pb-2">
                <button
                    onClick={() => setActiveTab('transactions')}
                    className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-all ${activeTab === 'transactions'
                            ? 'bg-cyan-500/20 text-cyan-400 border-b-2 border-cyan-400'
                            : 'text-slate-400 hover:text-white'
                        }`}
                >
                    Transaction Traces
                </button>
                <button
                    onClick={() => setActiveTab('agents')}
                    className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-all ${activeTab === 'agents'
                            ? 'bg-cyan-500/20 text-cyan-400 border-b-2 border-cyan-400'
                            : 'text-slate-400 hover:text-white'
                        }`}
                >
                    Agent Registry (KYA)
                </button>
            </div>

            {activeTab === 'transactions' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Transaction List */}
                    <motion.div
                        className="glass-card p-0 overflow-hidden"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                    >
                        <div className="p-4 border-b border-white/10 flex items-center gap-3">
                            <Search className="w-5 h-5 text-slate-400" />
                            <input
                                type="text"
                                placeholder="Search transactions..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="flex-1 bg-transparent text-white placeholder-slate-500 outline-none"
                            />
                        </div>

                        <div className="divide-y divide-white/5 max-h-[400px] overflow-y-auto">
                            {mockTransactions.map((tx) => (
                                <div
                                    key={tx.transaction_id}
                                    onClick={() => setSelectedTransaction(tx)}
                                    className={`p-4 cursor-pointer transition-all hover:bg-white/5 ${selectedTransaction?.transaction_id === tx.transaction_id
                                            ? 'bg-cyan-500/10 border-l-2 border-cyan-400'
                                            : ''
                                        }`}
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-3">
                                            <Shield className={`w-5 h-5 ${tx.status === 'completed' ? 'text-emerald-400' : 'text-rose-400'}`} />
                                            <div>
                                                <p className="font-mono text-cyan-400 text-sm">{tx.transaction_id}</p>
                                                <p className="text-xs text-slate-500">{tx.agent_id.split(':')[1]}</p>
                                            </div>
                                        </div>
                                        <span className={`badge ${tx.status === 'completed' ? 'badge-success' : 'badge-danger'}`}>
                                            {tx.status}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="text-slate-400">{new Date(tx.first_event).toLocaleString()}</span>
                                        <span className="text-slate-500">{tx.event_count} events</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>

                    {/* Event Timeline */}
                    <motion.div
                        className="glass-card"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                    >
                        <h3 className="text-lg font-semibold text-white mb-4">Event Timeline</h3>

                        {selectedTransaction ? (
                            <div className="space-y-3 max-h-[400px] overflow-y-auto">
                                {mockEvents.map((event, idx) => (
                                    <div
                                        key={event.event_id}
                                        onClick={() => setSelectedEvent(selectedEvent?.event_id === event.event_id ? null : event)}
                                        className={`p-3 rounded-xl cursor-pointer transition-all ${selectedEvent?.event_id === event.event_id
                                                ? 'bg-cyan-500/10 border border-cyan-500/30'
                                                : 'bg-slate-800/30 hover:bg-slate-800/50'
                                            }`}
                                    >
                                        <div className="flex items-center gap-3 mb-2">
                                            {getEventIcon(event.event_type)}
                                            <div className="flex-1">
                                                <p className="text-sm text-white font-medium">{event.action_taken}</p>
                                                <p className="text-xs text-slate-500">
                                                    {event.step_name || event.event_type.replace('_', ' ')}
                                                </p>
                                            </div>
                                            <span className="text-xs text-slate-500">
                                                {new Date(event.timestamp).toLocaleTimeString()}
                                            </span>
                                        </div>

                                        {selectedEvent?.event_id === event.event_id && (
                                            <motion.div
                                                initial={{ opacity: 0, height: 0 }}
                                                animate={{ opacity: 1, height: 'auto' }}
                                                className="mt-3 pt-3 border-t border-white/10 space-y-3"
                                            >
                                                {/* Reasoning Trace (THE WHY) */}
                                                <div>
                                                    <p className="text-xs text-cyan-400 font-medium mb-1">WHY (Reasoning Trace)</p>
                                                    <p className="text-sm text-slate-300">{event.reasoning_trace}</p>
                                                </div>

                                                {/* Decision Factors */}
                                                <div>
                                                    <p className="text-xs text-violet-400 font-medium mb-1">Decision Factors</p>
                                                    <div className="flex flex-wrap gap-1">
                                                        {event.decision_factors.map((factor, i) => (
                                                            <span key={i} className="px-2 py-0.5 bg-violet-500/10 text-violet-300 text-xs rounded-full">
                                                                {factor}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </div>

                                                {/* Validation Results */}
                                                {event.validation_results.length > 0 && (
                                                    <div>
                                                        <p className="text-xs text-emerald-400 font-medium mb-1">Validation Gates</p>
                                                        <div className="space-y-1">
                                                            {event.validation_results.map((v, i) => (
                                                                <div key={i} className={`text-xs p-2 rounded-lg ${v.passed
                                                                        ? 'bg-emerald-500/10 text-emerald-300'
                                                                        : 'bg-amber-500/10 text-amber-300'
                                                                    }`}>
                                                                    {v.passed ? '✓' : '⚠'} {v.gate_id}: {v.reason}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Agent Info (THE WHO) */}
                                                <div className="flex items-center gap-2 pt-2 border-t border-white/5">
                                                    <User className="w-3 h-3 text-slate-400" />
                                                    <span className="text-xs text-slate-400">Agent: {event.agent_id}</span>
                                                    <span className={`px-2 py-0.5 text-xs rounded-full border ${getAuthorityBadge(event.agent_authority)}`}>
                                                        {event.agent_authority}
                                                    </span>
                                                </div>
                                            </motion.div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-12 text-slate-400">
                                <Shield className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                <p>Select a transaction to view its audit trail</p>
                            </div>
                        )}
                    </motion.div>
                </div>
            )}

            {activeTab === 'agents' && (
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <Key className="w-5 h-5 text-cyan-400" />
                        Known Agents (KYA Framework)
                    </h3>

                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="text-left text-slate-400 text-sm border-b border-white/10">
                                    <th className="pb-3">Agent ID</th>
                                    <th className="pb-3">Type</th>
                                    <th className="pb-3">Version</th>
                                    <th className="pb-3">Authority</th>
                                    <th className="pb-3">Owner</th>
                                    <th className="pb-3">Description</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {mockAgents.map((agent) => (
                                    <tr key={agent.agent_id} className="text-sm hover:bg-white/5">
                                        <td className="py-3 font-mono text-cyan-400 text-xs">{agent.agent_id.slice(0, 30)}...</td>
                                        <td className="py-3 text-white">{agent.agent_type}</td>
                                        <td className="py-3 text-slate-400">{agent.version}</td>
                                        <td className="py-3">
                                            <span className={`px-2 py-1 text-xs rounded-full border ${getAuthorityBadge(agent.authority)}`}>
                                                {agent.authority}
                                            </span>
                                        </td>
                                        <td className="py-3 text-slate-400">{agent.owner}</td>
                                        <td className="py-3 text-slate-400">{agent.description}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </motion.div>
            )}
        </div>
    )
}
