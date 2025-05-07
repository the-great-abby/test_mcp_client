export default function Welcome({ onGetStarted }: { onGetStarted?: () => void }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-blue-200">
      <div className="bg-white shadow-lg rounded-xl p-8 max-w-md w-full flex flex-col items-center">
        <h1 className="text-3xl font-extrabold text-blue-700 mb-4">MCP Chat Client</h1>
        <p className="text-gray-700 mb-6 text-center">
          Welcome to the Model Context Protocol Chat Client!<br />
          Secure, real-time AI chat with advanced session and context management.
        </p>
        <button
          className="px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold shadow hover:bg-blue-700 transition"
          onClick={onGetStarted}
        >
          Get Started
        </button>
      </div>
    </div>
  );
} 