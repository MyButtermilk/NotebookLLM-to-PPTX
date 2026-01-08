'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { FiUpload, FiClock, FiSettings } from 'react-icons/fi'
import clsx from 'clsx'

export default function Navigation() {
  const pathname = usePathname()

  const links = [
    { href: '/', label: 'Convert', icon: FiUpload },
    { href: '/history', label: 'History', icon: FiClock },
    { href: '/settings', label: 'Settings', icon: FiSettings },
  ]

  return (
    <header className="border-b border-neu-dark/20 bg-neu-base">
      <nav className="container mx-auto px-6 py-4 max-w-7xl">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="neu-surface-sm w-12 h-12 flex items-center justify-center">
              <span className="text-2xl">📊</span>
            </div>
            <span className="font-display text-xl font-bold text-gray-800">
              SlideRefactor
            </span>
          </Link>

          <div className="flex items-center gap-2">
            {links.map((link) => {
              const Icon = link.icon
              const isActive = pathname === link.href

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={clsx(
                    'flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all',
                    isActive
                      ? 'neu-pressed text-primary-600'
                      : 'neu-button text-gray-600 hover:text-primary-600'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {link.label}
                </Link>
              )
            })}
          </div>
        </div>
      </nav>
    </header>
  )
}
