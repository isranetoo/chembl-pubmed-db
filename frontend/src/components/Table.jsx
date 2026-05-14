export default function Table({ columns, rows, emptyMessage = 'Sem registros.' }) {
  if (!rows?.length) {
    return <div className="rounded-xl glass p-8 text-sm text-white/30 text-center">{emptyMessage}</div>
  }
  return (
    <div className="overflow-hidden rounded-xl border border-white/[0.06] animate-fade-in">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-white/[0.06] text-left text-sm">
          <thead className="bg-white/[0.03]">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className="px-4 py-3.5 font-medium text-xs uppercase tracking-wider text-white/40">
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {rows.map((row, idx) => (
              <tr key={row.id || row.key || idx} className="align-top transition-colors hover:bg-white/[0.02]">
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3.5 text-white/70">
                    {col.render ? col.render(row) : row[col.key] ?? '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
