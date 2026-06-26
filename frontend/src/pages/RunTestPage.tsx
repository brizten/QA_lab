import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getTestCases, InputSchema, TestCase } from "../api/testCases";
import { queueTestRun } from "../api/testRuns";

export default function RunTestPage() {
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [selectedCode, setSelectedCode] = useState("");
  const [environment, setEnvironment] = useState("test");
  const [parametersText, setParametersText] = useState("{}");
  const [runId, setRunId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedTestCase = useMemo(
    () => testCases.find((testCase) => testCase.code === selectedCode),
    [selectedCode, testCases],
  );

  useEffect(() => {
    getTestCases({ is_active: true })
      .then((items) => {
        setTestCases(items);
        if (items.length > 0) {
          setSelectedCode(items[0].code);
          setParametersText(JSON.stringify(createDefaultParameters(items[0].input_schema), null, 2));
        }
      })
      .catch(() => setError("Could not load active test cases."));
  }, []);

  function handleSelectedCodeChange(code: string) {
    setSelectedCode(code);
    const testCase = testCases.find((item) => item.code === code);
    if (testCase) {
      setParametersText(JSON.stringify(createDefaultParameters(testCase.input_schema), null, 2));
    }
    setRunId(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setRunId(null);
    setIsSubmitting(true);

    try {
      const parsedParameters = JSON.parse(parametersText) as Record<string, unknown>;
      const queued = await queueTestRun({
        test_case_code: selectedCode,
        environment,
        parameters: parsedParameters,
      });
      setRunId(queued.run_id);
    } catch (caughtError) {
      if (caughtError instanceof SyntaxError) {
        setError("Parameters must be valid JSON.");
      } else {
        setError("Could not queue test run.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Run Test</h1>
        </div>
      </div>

      <form className="run-form" onSubmit={handleSubmit}>
        <label>
          Test case
          <select
            value={selectedCode}
            onChange={(event) => handleSelectedCodeChange(event.target.value)}
            required
          >
            {testCases.map((testCase) => (
              <option key={testCase.id} value={testCase.code}>
                {testCase.code}
              </option>
            ))}
          </select>
        </label>

        <label>
          Environment
          <input
            value={environment}
            onChange={(event) => setEnvironment(event.target.value)}
            required
          />
        </label>

        {selectedTestCase ? (
          <div className="schema-box">
            <strong>{selectedTestCase.name}</strong>
            <pre>{JSON.stringify(selectedTestCase.input_schema, null, 2)}</pre>
          </div>
        ) : null}

        <label>
          Parameters JSON
          <textarea
            rows={12}
            value={parametersText}
            onChange={(event) => setParametersText(event.target.value)}
            spellCheck={false}
            required
          />
        </label>

        {error ? <div className="alert error">{error}</div> : null}
        {runId ? (
          <div className="alert success">
            Run #{runId} queued.{" "}
            <Link to={`/test-runs/${runId}/report`}>Open report</Link>
          </div>
        ) : null}

        <button className="button primary" type="submit" disabled={!selectedCode || isSubmitting}>
          {isSubmitting ? "Queueing..." : "Queue Run"}
        </button>
      </form>
    </section>
  );
}

function createDefaultParameters(inputSchema: InputSchema): Record<string, unknown> {
  return Object.entries(getSchemaProperties(inputSchema)).reduce<Record<string, unknown>>(
    (accumulator, [key, rule]) => {
      const fieldRule = isFieldRule(rule) ? rule : {};

      if (key === "force_fail") {
        accumulator[key] = false;
        return accumulator;
      }

      if (fieldRule.type === "number") {
        accumulator[key] = 0;
      } else if (fieldRule.type === "boolean") {
        accumulator[key] = false;
      } else {
        accumulator[key] = "";
      }
      return accumulator;
    },
    {},
  );
}

function getSchemaProperties(inputSchema: InputSchema): Record<string, unknown> {
  const properties = inputSchema.properties;
  if (properties && typeof properties === "object" && !Array.isArray(properties)) {
    return properties as Record<string, unknown>;
  }
  return inputSchema;
}

function isFieldRule(value: unknown): value is { type?: string } {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
