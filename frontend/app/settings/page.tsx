'use client'

import { useState, useEffect } from 'react'
import { FiCheck, FiX, FiEye, FiEyeOff, FiRefreshCw } from 'react-icons/fi'
import axios from 'axios'

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    datalab_api_key: '',
    anthropic_api_key: '',
    default_extractor: 'datalab',
    default_preprocessing: false,
  })

  const [showKeys, setShowKeys] = useState({
    datalab: false,
    anthropic: false,
  })

  const [testResults, setTestResults] = useState<Record<string, any>>({})
  const [testing, setTesting] = useState<Record<string, boolean>>({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/settings')
      setSettings(response.data)
    } catch (error) {
      console.error('Failed to load settings:', error)
    }
  }

  const handleSave = async () => {
    try {
      await axios.post('http://localhost:8000/api/settings', settings)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (error) {
      console.error('Failed to save settings:', error)
      alert('Failed to save settings')
    }
  }

  const testConnection = async (provider: string) => {
    setTesting({ ...testing, [provider]: true })

    try {
      const response = await axios.post('http://localhost:8000/api/settings/test-connection', null, {
        params: { provider }
      })
      setTestResults({ ...testResults, [provider]: response.data })
    } catch (error: any) {
      setTestResults({
        ...testResults,
        [provider]: {
          status: 'error',
          message: error.response?.data?.detail || 'Connection failed'
        }
      })
    } finally {
      setTesting({ ...testing, [provider]: false })
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold text-gray-800">Settings</h1>
        <p className="text-gray-600 mt-2">Configure API keys and default conversion options</p>
      </div>

      {/* API Providers Section */}
      <div className="neu-card p-8 space-y-6">
        <h2 className="text-xl font-semibold text-gray-800">API Providers</h2>

        {/* Datalab */}
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">
            Datalab API Key
            <span className="text-xs text-gray-500 ml-2">(Primary extractor)</span>
          </label>
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <input
                type={showKeys.datalab ? 'text' : 'password'}
                value={settings.datalab_api_key}
                onChange={(e) => setSettings({ ...settings, datalab_api_key: e.target.value })}
                placeholder="Enter your Datalab API key"
                className="w-full neu-input px-4 py-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
              <button
                type="button"
                onClick={() => setShowKeys({ ...showKeys, datalab: !showKeys.datalab })}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showKeys.datalab ? <FiEyeOff /> : <FiEye />}
              </button>
            </div>
            <button
              onClick={() => testConnection('datalab')}
              disabled={testing.datalab || !settings.datalab_api_key}
              className="neu-button px-4 py-3 text-gray-700 hover:text-primary-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {testing.datalab ? (
                <>
                  <FiRefreshCw className="animate-spin" />
                  Testing...
                </>
              ) : (
                'Test'
              )}
            </button>
          </div>
          {testResults.datalab && (
            <div className={`flex items-center gap-2 text-sm ${
              testResults.datalab.status === 'success' ? 'text-success' : 'text-error'
            }`}>
              {testResults.datalab.status === 'success' ? <FiCheck /> : <FiX />}
              {testResults.datalab.message}
              {testResults.datalab.latency_ms && ` (${testResults.datalab.latency_ms}ms)`}
            </div>
          )}
        </div>

        {/* Anthropic */}
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">
            Anthropic API Key
            <span className="text-xs text-gray-500 ml-2">(Claude for AI processing)</span>
          </label>
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <input
                type={showKeys.anthropic ? 'text' : 'password'}
                value={settings.anthropic_api_key}
                onChange={(e) => setSettings({ ...settings, anthropic_api_key: e.target.value })}
                placeholder="Enter your Anthropic API key"
                className="w-full neu-input px-4 py-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
              <button
                type="button"
                onClick={() => setShowKeys({ ...showKeys, anthropic: !showKeys.anthropic })}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showKeys.anthropic ? <FiEyeOff /> : <FiEye />}
              </button>
            </div>
            <button
              onClick={() => testConnection('anthropic')}
              disabled={testing.anthropic || !settings.anthropic_api_key}
              className="neu-button px-4 py-3 text-gray-700 hover:text-primary-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {testing.anthropic ? (
                <>
                  <FiRefreshCw className="animate-spin" />
                  Testing...
                </>
              ) : (
                'Test'
              )}
            </button>
          </div>
          {testResults.anthropic && (
            <div className={`flex items-center gap-2 text-sm ${
              testResults.anthropic.status === 'success' ? 'text-success' : 'text-error'
            }`}>
              {testResults.anthropic.status === 'success' ? <FiCheck /> : <FiX />}
              {testResults.anthropic.message}
              {testResults.anthropic.latency_ms && ` (${testResults.anthropic.latency_ms}ms)`}
            </div>
          )}
        </div>
      </div>

      {/* Conversion Defaults Section */}
      <div className="neu-card p-8 space-y-6">
        <h2 className="text-xl font-semibold text-gray-800">Conversion Defaults</h2>

        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">
            Default Extractor
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="extractor"
                value="datalab"
                checked={settings.default_extractor === 'datalab'}
                onChange={(e) => setSettings({ ...settings, default_extractor: e.target.value })}
                className="w-4 h-4 text-primary-600"
              />
              <span className="text-gray-700">Datalab (SOTA)</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="extractor"
                value="paddleocr"
                checked={settings.default_extractor === 'paddleocr'}
                onChange={(e) => setSettings({ ...settings, default_extractor: e.target.value })}
                className="w-4 h-4 text-primary-600"
              />
              <span className="text-gray-700">PaddleOCR (Open Source)</span>
            </label>
          </div>
        </div>

        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.default_preprocessing}
              onChange={(e) => setSettings({ ...settings, default_preprocessing: e.target.checked })}
              className="w-5 h-5 text-primary-600 rounded"
            />
            <div>
              <div className="text-sm font-medium text-gray-700">Enable preprocessing by default</div>
              <div className="text-xs text-gray-500">Apply OpenCV enhancements (deskew, denoise, sharpen)</div>
            </div>
          </label>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end gap-4">
        <button
          onClick={handleSave}
          className="neu-button px-8 py-3 font-semibold text-primary-600 hover:text-primary-700 flex items-center gap-2"
        >
          {saved ? (
            <>
              <FiCheck />
              Saved!
            </>
          ) : (
            'Save Settings'
          )}
        </button>
      </div>
    </div>
  )
}
