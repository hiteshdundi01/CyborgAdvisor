import { useState } from 'react'
import { motion } from 'framer-motion'
import { Plus, Trash2, Edit2, Save, X } from 'lucide-react'

interface Holding {
    id: string
    asset: string
    assetClass: string
    value: number
    quantity: number
}

const initialHoldings: Holding[] = [
    { id: '1', asset: 'AAPL', assetClass: 'stocks', value: 25000, quantity: 145 },
    { id: '2', asset: 'MSFT', assetClass: 'stocks', value: 20000, quantity: 52 },
    { id: '3', asset: 'GOOGL', assetClass: 'stocks', value: 15000, quantity: 108 },
    { id: '4', asset: 'BND', assetClass: 'bonds', value: 20000, quantity: 270 },
    { id: '5', asset: 'TLT', assetClass: 'bonds', value: 10000, quantity: 100 },
    { id: '6', asset: 'CASH', assetClass: 'cash', value: 8000, quantity: 8000 },
    { id: '7', asset: 'GLD', assetClass: 'alternatives', value: 2000, quantity: 11 },
]

const assetClassColors: Record<string, string> = {
    stocks: 'bg-cyan-500/20 text-cyan-400',
    bonds: 'bg-emerald-500/20 text-emerald-400',
    cash: 'bg-amber-500/20 text-amber-400',
    alternatives: 'bg-violet-500/20 text-violet-400',
}

export default function PortfolioManager() {
    const [holdings, setHoldings] = useState<Holding[]>(initialHoldings)
    const [editingId, setEditingId] = useState<string | null>(null)
    const [editValues, setEditValues] = useState<Partial<Holding>>({})

    const totalValue = holdings.reduce((sum, h) => sum + h.value, 0)

    const startEdit = (holding: Holding) => {
        setEditingId(holding.id)
        setEditValues({ ...holding })
    }

    const saveEdit = () => {
        if (editingId && editValues) {
            setHoldings(holdings.map(h =>
                h.id === editingId ? { ...h, ...editValues } as Holding : h
            ))
            setEditingId(null)
            setEditValues({})
        }
    }

    const cancelEdit = () => {
        setEditingId(null)
        setEditValues({})
    }

    const deleteHolding = (id: string) => {
        setHoldings(holdings.filter(h => h.id !== id))
    }

    const addHolding = () => {
        const newHolding: Holding = {
            id: Date.now().toString(),
            asset: 'NEW',
            assetClass: 'stocks',
            value: 0,
            quantity: 0,
        }
        setHoldings([...holdings, newHolding])
        startEdit(newHolding)
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-1">Portfolio Manager</h1>
                    <p className="text-slate-400">Manage your holdings and asset allocation.</p>
                </div>
                <button onClick={addHolding} className="btn-primary flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    Add Holding
                </button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <p className="text-slate-400 text-sm mb-1">Total Value</p>
                    <p className="text-2xl font-bold text-white">${totalValue.toLocaleString()}</p>
                </motion.div>

                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                >
                    <p className="text-slate-400 text-sm mb-1">Holdings</p>
                    <p className="text-2xl font-bold text-white">{holdings.length}</p>
                </motion.div>

                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <p className="text-slate-400 text-sm mb-1">Asset Classes</p>
                    <p className="text-2xl font-bold text-white">
                        {new Set(holdings.map(h => h.assetClass)).size}
                    </p>
                </motion.div>

                <motion.div
                    className="glass-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                >
                    <p className="text-slate-400 text-sm mb-1">Largest Position</p>
                    <p className="text-2xl font-bold text-white">
                        {holdings.sort((a, b) => b.value - a.value)[0]?.asset || '-'}
                    </p>
                </motion.div>
            </div>

            {/* Holdings Table */}
            <motion.div
                className="glass-card p-0 overflow-hidden"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 }}
            >
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Asset</th>
                            <th>Class</th>
                            <th>Value</th>
                            <th>Quantity</th>
                            <th>Weight</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {holdings.map((holding) => (
                            <tr key={holding.id}>
                                <td>
                                    {editingId === holding.id ? (
                                        <input
                                            type="text"
                                            value={editValues.asset || ''}
                                            onChange={(e) => setEditValues({ ...editValues, asset: e.target.value })}
                                            className="w-24"
                                        />
                                    ) : (
                                        <span className="font-medium text-white">{holding.asset}</span>
                                    )}
                                </td>
                                <td>
                                    {editingId === holding.id ? (
                                        <select
                                            value={editValues.assetClass || ''}
                                            onChange={(e) => setEditValues({ ...editValues, assetClass: e.target.value })}
                                            className="w-32"
                                        >
                                            <option value="stocks">Stocks</option>
                                            <option value="bonds">Bonds</option>
                                            <option value="cash">Cash</option>
                                            <option value="alternatives">Alternatives</option>
                                        </select>
                                    ) : (
                                        <span className={`badge ${assetClassColors[holding.assetClass]}`}>
                                            {holding.assetClass}
                                        </span>
                                    )}
                                </td>
                                <td>
                                    {editingId === holding.id ? (
                                        <input
                                            type="number"
                                            value={editValues.value || ''}
                                            onChange={(e) => setEditValues({ ...editValues, value: Number(e.target.value) })}
                                            className="w-28"
                                        />
                                    ) : (
                                        <span className="text-slate-200">${holding.value.toLocaleString()}</span>
                                    )}
                                </td>
                                <td>
                                    {editingId === holding.id ? (
                                        <input
                                            type="number"
                                            value={editValues.quantity || ''}
                                            onChange={(e) => setEditValues({ ...editValues, quantity: Number(e.target.value) })}
                                            className="w-24"
                                        />
                                    ) : (
                                        <span className="text-slate-200">{holding.quantity}</span>
                                    )}
                                </td>
                                <td>
                                    <span className="text-slate-200">
                                        {((holding.value / totalValue) * 100).toFixed(1)}%
                                    </span>
                                </td>
                                <td>
                                    <div className="flex items-center gap-2">
                                        {editingId === holding.id ? (
                                            <>
                                                <button
                                                    onClick={saveEdit}
                                                    className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
                                                >
                                                    <Save className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={cancelEdit}
                                                    className="p-2 rounded-lg bg-slate-500/20 text-slate-400 hover:bg-slate-500/30"
                                                >
                                                    <X className="w-4 h-4" />
                                                </button>
                                            </>
                                        ) : (
                                            <>
                                                <button
                                                    onClick={() => startEdit(holding)}
                                                    className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30"
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => deleteHolding(holding.id)}
                                                    className="p-2 rounded-lg bg-rose-500/20 text-rose-400 hover:bg-rose-500/30"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </motion.div>
        </div>
    )
}
