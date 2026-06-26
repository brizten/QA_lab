import { FormEvent, useEffect, useState } from "react";

import { getModules, Module } from "../api/modules";
import { getTestCases, TestCase } from "../api/testCases";

export default function TestCasesPage() {
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [modules, setModules] = useState<Module[]>([]);
  const [moduleId, setModuleId] = useState("");
  const [tag, setTag] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function loadTestCases() {
    setIsLoading(true);
    setError(null);
    getTestCases({
      module_id: moduleId ? Number(moduleId) : undefined,
      tag: tag || undefined,
      is_active: activeOnly ? true : undefined,
    })
      .then(setTestCases)
      .catch(() => setError("Could not load test cases."))
      .finally(() => setIsLoading(false));
  }

  useEffect(() => {
    getModules().then(setModules).catch(() => setModules([]));
    loadTestCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    loadTestCases();
  }

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Test Cases</h1>
        </div>
      </div>
      <form className="toolbar" onSubmit={handleSubmit}>
        <label>
          Module
          <select value={moduleId} onChange={(event) => setModuleId(event.target.value)}>
            <option value="">All modules</option>
            {modules.map((module) => (
              <option key={module.id} value={module.id}>
                {module.code}
              </option>
            ))}
          </select>
        </label>
        <label>
          Tag
          <input value={tag} onChange={(event) => setTag(event.target.value)} placeholder="business" />
        </label>
        <label className="checkbox-label">
          <input
            checked={activeOnly}
            type="checkbox"
            onChange={(event) => setActiveOnly(event.target.checked)}
          />
          Active only
        </label>
        <button className="button secondary" type="submit">
          Apply
        </button>
      </form>
      {error ? <div className="alert error">{error}</div> : null}
      {isLoading ? <div className="muted">Loading test cases...</div> : null}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Code</th>
              <th>Name</th>
              <th>Module</th>
              <th>Tags</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {testCases.map((testCase) => (
              <tr key={testCase.id}>
                <td>#{testCase.id}</td>
                <td className="code">{testCase.code}</td>
                <td>{testCase.name}</td>
                <td>{modules.find((module) => module.id === testCase.module_id)?.code || testCase.module_id}</td>
                <td>
                  <div className="tag-list">
                    {testCase.tags.map((item) => (
                      <span className="tag" key={item}>
                        {item}
                      </span>
                    ))}
                  </div>
                </td>
                <td>{testCase.is_active ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
