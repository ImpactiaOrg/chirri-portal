type Props = {
  size?: number;
  variant?: "pulse" | "rotate";
};

export function ChSpinner({ size = 64, variant = "pulse" }: Props) {
  const animation =
    variant === "rotate"
      ? "ch-spin-rotate 1.2s ease-in-out infinite"
      : "ch-spin-pulse 1.1s ease-in-out infinite";

  return (
    <div
      role="status"
      aria-label="Cargando"
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.22,
        background: "var(--chirri-black)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        animation,
        boxShadow: `${size * 0.06}px ${size * 0.06}px 0 var(--chirri-pink-deep)`,
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 900,
          fontSize: size * 0.7,
          color: "var(--chirri-yellow)",
          letterSpacing: "-0.04em",
          display: "inline-block",
          transform: "scaleY(1.2)",
          transformOrigin: "center",
          lineHeight: 0.9,
          WebkitTextStroke: `${size * 0.008}px currentColor`,
          userSelect: "none",
        }}
      >
        ch
      </span>
    </div>
  );
}
