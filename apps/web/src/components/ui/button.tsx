import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-control text-sm font-medium transition-colors focus-visible:outline-none focus-visible:shadow-focus disabled:pointer-events-none disabled:opacity-40",
  {
    variants: {
      variant: {
        primary:
          "border border-[#8251ff] bg-[linear-gradient(90deg,#7647ff,#9462ff)] text-white hover:shadow-[0_0_24px_rgba(139,92,246,0.22)]",
        ghost: "text-ink hover:bg-white/5",
        outline: "border border-line bg-[#0e131c] text-ink hover:border-[#495a79]",
        live: "bg-live text-white hover:bg-[#E11D48]",
      },
      size: {
        default: "h-10 px-4",
        lg: "h-12 px-6 text-base",
        sm: "h-8 px-3 text-xs",
      },
    },
    defaultVariants: { variant: "primary", size: "default" },
  },
);

export { buttonVariants };

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>
>(({ className, variant, size, ...props }, ref) => (
  <button
    ref={ref}
    className={cn(buttonVariants({ variant, size }), className)}
    {...props}
  />
));
Button.displayName = "Button";
