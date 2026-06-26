import { useEffect, useState } from "react";

import { getModules, Module } from "../api/modules";

export default function ModulesPage() {
  const [modules, setModules] = useState<Module[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getModules()
      .then(setModules)
      .catch(() => setError("Could not load modules."))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Modules</h1>
        </div>
      </div>
      {error ? <div className="alert error">{error}</div> : null}
      {isLoading ? <div className="muted">Loading modules...</div> : null}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {modules.map((module) => (
              <tr key={module.id}>
                <td className="code">{module.code}</td>
                <td>{module.name}</td>
                <td>{module.description || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
