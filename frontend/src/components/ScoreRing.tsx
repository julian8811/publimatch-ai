export default function ScoreRing({ score }: { score: number }) {
  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  
  const colorClass = score > 75 ? "text-violet-500" : score > 50 ? "text-yellow-500" : "text-red-500";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg className="w-20 h-20 transform -rotate-90">
        <circle
          className="text-white/10"
          strokeWidth="6"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx="40"
          cy="40"
        />
        <circle
          className={`${colorClass} transition-all duration-1000 ease-out`}
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx="40"
          cy="40"
        />
      </svg>
      <div className="absolute text-xl font-bold">
        {Math.round(score)}
      </div>
    </div>
  );
}
