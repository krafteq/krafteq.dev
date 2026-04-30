import { useState } from "react";
import PatternForm from "./components/PatternForm.jsx";
import PatternOutput from "./components/PatternOutput.jsx";
import { compute, buildInstructions, validateInputs } from "./patterns/raglanMockNeck.js";

export default function App() {
  const [output, setOutput]   = useState(null);  // generated instruction string
  const [errors, setErrors]   = useState([]);

  const handleGenerate = (gauge, measurements) => {
    const errs = validateInputs(gauge, measurements);
    if (errs.length) {
      setErrors(errs);
      setOutput(null);
      return;
    }
    setErrors([]);
    const stats = compute(gauge, measurements);
    setOutput(buildInstructions(stats));
  };

  return (
    <div className="min-h-screen bg-stone-50">
      <div className="max-w-2xl mx-auto px-4 py-10">

        {/* Header */}
        <header className="mb-10">
          <h1 className="text-2xl font-semibold text-stone-900 tracking-tight">
            Knitwit
          </h1>
          <p className="text-sm text-stone-400 mt-1">
            Sweater pattern generator — gauge in, instructions out.
          </p>
        </header>

        {/* Form */}
        <PatternForm onGenerate={handleGenerate} />

        {/* Output */}
        {(output || errors.length > 0) && (
          <div className="mt-8">
            <PatternOutput text={output} errors={errors} />
          </div>
        )}

      </div>
    </div>
  );
}
