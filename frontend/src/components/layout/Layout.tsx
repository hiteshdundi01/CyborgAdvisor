import { Outlet, NavLink } from 'react-router-dom'
import {
    LayoutDashboard,
    Briefcase,
    RefreshCw,
    TrendingDown,
    Activity,
    Settings,
    HelpCircle,
    Shield,
    Sliders
} from 'lucide-react'

const navigation = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Portfolio', href: '/portfolio', icon: Briefcase },
    { name: 'Rebalance', href: '/rebalance', icon: RefreshCw },
    { name: 'Tax Loss Harvesting', href: '/tax-loss-harvesting', icon: TrendingDown },
    { name: 'Direct Indexing', href: '/direct-indexing', icon: Sliders },
    { name: 'Saga Monitor', href: '/saga-monitor', icon: Activity },
    { name: 'Audit Monitor', href: '/audit', icon: Shield },
]

export default function Layout() {
    return (
        <div className="flex min-h-screen">
            {/* Sidebar */}
            <aside className="sidebar">
                {/* Logo */}
                <div className="flex items-center gap-3 mb-8 px-2">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center">
                        <span className="text-xl">🤖</span>
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-white">Cyborg Advisor</h1>
                        <p className="text-xs text-slate-400">Neurosymbolic AI</p>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1">
                    {navigation.map((item) => (
                        <NavLink
                            key={item.name}
                            to={item.href}
                            className={({ isActive }) =>
                                `sidebar-link ${isActive ? 'active' : ''}`
                            }
                        >
                            <item.icon className="w-5 h-5" />
                            <span>{item.name}</span>
                        </NavLink>
                    ))}
                </nav>

                {/* Footer */}
                <div className="mt-auto pt-4 border-t border-white/10">
                    <NavLink to="/settings" className="sidebar-link">
                        <Settings className="w-5 h-5" />
                        <span>Settings</span>
                    </NavLink>
                    <NavLink to="/help" className="sidebar-link">
                        <HelpCircle className="w-5 h-5" />
                        <span>Help</span>
                    </NavLink>
                </div>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                <Outlet />
            </main>
        </div>
    )
}
