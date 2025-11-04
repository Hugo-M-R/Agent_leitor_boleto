import { useEffect, useMemo, useState } from 'react'

function JsonView({ data }) {
  const pretty = useMemo(() => {
    try { return JSON.stringify(data, null, 2) } catch { return String(data ?? '') }
  }, [data])
  return (
    <pre className="text-xs text-slate-300 max-h-[420px] overflow-auto whitespace-pre-wrap">
      {pretty}
    </pre>
  )
}

export default function App() {
  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  const [health, setHealth] = useState('...')
  const [file, setFile] = useState(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [pathInput, setPathInput] = useState('dados/Modelo-de-Boleto.pdf')
  const [byPathLoading, setByPathLoading] = useState(false)
  const [byPathResult, setByPathResult] = useState(null)
  const [returnsLoading, setReturnsLoading] = useState(false)
  const [returnsItems, setReturnsItems] = useState([])
  const [selectedItem, setSelectedItem] = useState(null)
  const [selectedContent, setSelectedContent] = useState(null)
  const [selectedLoading, setSelectedLoading] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/health`).then(r => r.json()).then(d => setHealth(d.status || 'ok')).catch(() => setHealth('erro'))
  }, [API_BASE])

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return
    setUploadLoading(true)
    setUploadResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`${API_BASE}/extract/`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setUploadResult(data)
    } catch (err) {
      setUploadResult({ error: String(err) })
    } finally {
      setUploadLoading(false)
    }
  }

  async function handleByPath(e) {
    e.preventDefault()
    if (!pathInput) return
    setByPathLoading(true)
    setByPathResult(null)
    try {
      const res = await fetch(`${API_BASE}/extract/by-path`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: pathInput })
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setByPathResult(data)
    } catch (err) {
      setByPathResult({ error: String(err) })
    } finally {
      setByPathLoading(false)
    }
  }

  async function refreshReturns() {
    setReturnsLoading(true)
    setReturnsItems([])
    setSelectedItem(null)
    setSelectedContent(null)
    try {
      const res = await fetch(`${API_BASE}/extract/returns`)
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setReturnsItems(Array.isArray(data.items) ? data.items : [])
    } catch {
      setReturnsItems([])
    } finally {
      setReturnsLoading(false)
    }
  }

  async function openItem(item) {
    setSelectedItem(item)
    setSelectedLoading(true)
    setSelectedContent(null)
    try {
      const url = new URL(`${API_BASE}/extract/returns/file`)
      url.searchParams.set('path', item.path)
      const res = await fetch(url)
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setSelectedContent(data)
    } catch (err) {
      setSelectedContent({ error: String(err) })
    } finally {
      setSelectedLoading(false)
    }
  }

  return (
    <div className="min-h-full bg-[#0b0f17] text-slate-100">
      <div className="max-w-7xl mx-auto p-6">
        <header className="flex items-center justify-between mb-6">
          <div>
            <h1 className="m-0 text-2xl font-semibold">Leitor de Boleto</h1>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs ${health === 'ok' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>API: {health}</span>
          </div>
          <code className="px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-slate-400">{API_BASE}</code>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950">
              <h2 className="m-0 text-base font-semibold">Upload de arquivo</h2>
            </div>
            <div className="p-4 space-y-3">
              <form className="flex gap-3 items-center" onSubmit={handleUpload}>
                <input className="flex-1 file:mr-3 file:px-3 file:py-2 file:rounded-lg file:border-0 file:bg-slate-800 file:text-slate-300 file:cursor-pointer px-3 py-2 rounded-lg border border-slate-800 bg-slate-900/50" type="file" accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} />
                <button className="btn btn-primary" type="submit" disabled={!file || uploadLoading}>{uploadLoading ? 'Enviando...' : 'Extrair'}</button>
              </form>
              {uploadResult && (
                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                  <h3 className="m-0 mb-2 font-semibold">Resultado</h3>
                  <JsonView data={uploadResult} />
                </div>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950">
              <h2 className="m-0 text-base font-semibold">Extrair por caminho</h2>
            </div>
            <div className="p-4 space-y-3">
              <form className="flex gap-3 items-center" onSubmit={handleByPath}>
                <input className="flex-1 px-3 py-2 rounded-lg border border-slate-800 bg-slate-900/50" type="text" value={pathInput} onChange={(e) => setPathInput(e.target.value)} placeholder="Ex.: dados/Modelo-de-Boleto.pdf" />
                <button className="btn btn-primary" type="submit" disabled={!pathInput || byPathLoading}>{byPathLoading ? 'Processando...' : 'Extrair'}</button>
              </form>
              {byPathResult && (
                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                  <h3 className="m-0 mb-2 font-semibold">Resultado</h3>
                  <JsonView data={byPathResult} />
                </div>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden lg:col-span-2">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950">
              <h2 className="m-0 text-base font-semibold">Retornos salvos</h2>
              <button className="btn btn-outline" onClick={refreshReturns} disabled={returnsLoading}>{returnsLoading ? 'Carregando...' : 'Atualizar'}</button>
            </div>
            <div className="p-4 grid grid-cols-[280px,1fr] gap-3">
              <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-2 max-h-[520px] overflow-auto">
                {returnsItems.length === 0 && !returnsLoading && (
                  <div className="text-sm text-slate-400 px-2 py-1">Nenhum retorno carregado. Clique em Atualizar.</div>
                )}
                <div className="flex flex-col gap-1">
                  {returnsItems.map((it) => (
                    <button key={it.path} className={`text-left px-2 py-2 rounded-md border ${selectedItem?.path === it.path ? 'bg-blue-500/10 border-blue-500/40' : 'bg-transparent border-transparent hover:bg-white/5'}`} onClick={() => openItem(it)}>
                      <span className={`text-[11px] px-2 py-0.5 rounded-full mr-2 ${it.type === 'extracao' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-blue-500/15 text-blue-400'}`}>{it.type}</span>
                      <span className="align-middle">{it.name}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                {!selectedItem && <div className="text-sm text-slate-400">Selecione um item para visualizar</div>}
                {selectedItem && (
                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <div className="flex items-center justify-between mb-2 gap-3">
                      <strong className="truncate">{selectedItem.name}</strong>
                      <code className="text-xs text-slate-400 bg-white/5 px-2 py-0.5 rounded" title={selectedItem.path}>{selectedItem.path}</code>
                    </div>
                    {selectedLoading ? <div className="text-slate-400">Carregando...</div> : <JsonView data={selectedContent} />}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <footer className="mt-7 flex justify-center text-xs text-slate-400">Frontend • React + Vite + Tailwind</footer>
      </div>
    </div>
  )
}
