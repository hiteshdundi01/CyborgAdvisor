import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react'



// Mock data - replace with API calls
const portfolioData = [
    { name: 'Stocks', value: 60000, percentage: 60, color: '#06b6d4' },
    { name: 'Bonds', value: 30000, percentage: 30, color: '#10b981' },
    { name: 'Cash', value: 8000, percentage: 8, color: '#f59e0b' },
    { name: 'Alternatives', value: 2000, percentage: 2, color: '#8b5cf6' },
]

const recentActivity = [
    { id: 1, action: 'Rebalance Completed', status: 'success', time: '2 hours ago' },
    { id: 2, action: 'TLH Opportunity Found', status: 'info', time: '4 hours ago' },
    { id: 3, action: 'Compliance Check Passed', status: 'success', time: '1 day ago' },
]

export default function Dashboard() {
    const totalValue = portfolioData.reduce((sum, item) => sum + item.value, 0)

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-1">Dashboard</h1>
                    <p className="text-slate-400">Welcome back! Here's your portfolio overview.</p>
                </div>
                <button className="btn-primary flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    Run Analysis
                </button>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                >
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-slate-400 text-sm">Total Value</span>
                        <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center">
                            <DollarSign className="w-5 h-5 text-cyan-400" />
                        </div>
                    </div>
                    <p className="text-2xl font-bold text-white">${totalValue.toLocaleString()}</p>
                    <p className="text-sm text-emerald-400 flex items-center gap-1 mt-2">
                        <TrendingUp className="w-4 h-4" />
                        +5.2% from last month
                    </p>
                </motion.div>

                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-slate-400 text-sm">TLH Opportunities</span>
                        <div className="w-10 h-10 rounded-xl bg-rose-500/20 flex items-center justify-center">
                            <TrendingDown className="w-5 h-5 text-rose-400" />
                        </div>
                    </div>
                    <p className="text-2xl font-bold text-white">$4,250</p>
                    <p className="text-sm text-slate-400 mt-2">
                        Potential tax savings: $1,233
                    </p>
                </motion.div>

                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                >
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-slate-400 text-sm">Drift from Target</span>
                        <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                            <Activity className="w-5 h-5 text-amber-400" />
                        </div>
                    </div>
                    <p className="text-2xl font-bold text-white">2.3%</p>
                    <p className="text-sm text-amber-400 mt-2">
                        Rebalance recommended
                    </p>
                </motion.div>

                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                >
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-slate-400 text-sm">Sagas Executed</span>
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                            <Activity className="w-5 h-5 text-emerald-400" />
                        </div>
                    </div>
                    <p className="text-2xl font-bold text-white">12</p>
                    <p className="text-sm text-emerald-400 mt-2">
                        100% success rate
                    </p>
                </motion.div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Allocation Chart */}
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3 }}
                >
                    <h3 className="text-lg font-semibold text-white mb-4">Asset Allocation</h3>
                    <div className="flex items-center">
                        <div className="w-1/2">
                            <ResponsiveContainer width="100%" height={200}>
                                <PieChart>
                                    <Pie
                                        data={portfolioData}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={60}
                                        outerRadius={80}
                                        paddingAngle={4}
                                        dataKey="value"
                                    >
                                        {portfolioData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Pie>
                                    <Tooltip
                                        contentStyle={{
                                            background: '#1e293b',
                                            border: '1px solid rgba(255,255,255,0.1)',
                                            borderRadius: '8px',
                                            color: '#e2e8f0'
                                        }}
                                        formatter={(value) => `$${Number(value).toLocaleString()}`}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="w-1/2 space-y-3">
                            {portfolioData.map((item) => (
                                <div key={item.name} className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div
                                            className="w-3 h-3 rounded-full"
                                            style={{ backgroundColor: item.color }}
                                        />
                                        <span className="text-slate-300 text-sm">{item.name}</span>
                                    </div>
                                    <span className="text-white font-medium">{item.percentage}%</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </motion.div>

                {/* Recent Activity */}
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.4 }}
                >
                    <h3 className="text-lg font-semibold text-white mb-4">Recent Activity</h3>
                    <div className="space-y-3">
                        {recentActivity.map((item) => (
                            <div
                                key={item.id}
                                className="flex items-center justify-between p-3 rounded-xl bg-slate-800/30"
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`w-2 h-2 rounded-full ${item.status === 'success' ? 'bg-emerald-400' : 'bg-cyan-400'
                                        }`} />
                                    <span className="text-slate-200">{item.action}</span>
                                </div>
                                <span className="text-slate-500 text-sm">{item.time}</span>
                            </div>
                        ))}
                    </div>
                </motion.div>
            </div>

            {/* System Architecture Callout */}
            <motion.div
                className="glass-card border-l-4 border-cyan-400"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
            >
                <div className="flex items-start gap-4">
                    <div className="text-3xl">🧠</div>
                    <div>
                        <h3 className="text-lg font-semibold text-white mb-1">Neurosymbolic Architecture</h3>
                        <p className="text-slate-400">
                            <span className="text-emerald-400">System 1 (LLM)</span> handles intent parsing.
                            <span className="text-amber-400"> System 2 (Python)</span> handles calculations.
                            100% deterministic financial operations.
                        </p>
                    </div>
                </div>
            </motion.div>
        </div>
    )
}
