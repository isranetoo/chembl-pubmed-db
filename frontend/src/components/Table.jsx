export default function Table({ columns, rows, emptyMessage = 'Sem registros.' }) {
  if (!rows?.length) {
    return <div className="rounded-2xl border border-dashed border-white/10 p-8 text-sm text-slate-400">{emptyMessage}</div>
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-white/10 text-left text-sm">
          <thead className="bg-white/5 text-slate-300">
            <tr>
              {columns.map((column) => (
                <th key={column.key} className="px-4 py-3 font-medium">
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 bg-slate-950/50">
            {rows.map((row, index) => (
              <tr key={row.id || row.key || index} className="align-top">
                {columns.map((column) => (
                  <td key={column.key} className="px-4 py-3 text-slate-200">
                    {column.render ? column.render(row) : row[column.key] ?? '—'}
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
