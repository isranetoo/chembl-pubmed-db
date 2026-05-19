export default function Table({ columns, rows, emptyMessage = 'Sem registros.' }) {
  if (!rows?.length) {
    return (
      <div className="rounded-xl bg-white border border-gray-200 p-8 text-sm text-neutral-500 text-center">
        {emptyMessage}
      </div>
    )
  }
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm animate-fade-in">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-3.5 font-semibold text-xs uppercase tracking-wider text-gray-500"
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((row, idx) => (
              <tr key={row.id || row.key || idx} className="align-top transition-colors hover:bg-green-50/40">
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3.5 text-gray-700">
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
