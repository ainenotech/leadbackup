import React from "react";

interface HeaderBannerProps {
  title: string;
  subtitle: string;
  badgeText?: string;
  badgeType?: "live" | "master" | "draft" | "sent";
  action?: React.ReactNode;
}

export default function HeaderBanner({
  title,
  subtitle,
  badgeText,
  badgeType = "live",
  action,
}: HeaderBannerProps) {
  let badgeClass = "badge-pending";
  if (badgeType === "live" || badgeType === "sent") {
    badgeClass = "badge-sent";
  } else if (badgeType === "draft") {
    badgeClass = "badge-drafted";
  }

  return (
    <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 mb-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] flex justify-between items-center flex-wrap gap-3">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-[#0F172A] flex items-center gap-2.5 tracking-tight">
          <span>{title}</span>
          {badgeText && (
            <span className={`badge ${badgeClass} text-[11px] font-semibold`}>
              {badgeText}
            </span>
          )}
        </h1>
        <p className="text-[13.5px] text-[#64748B] mt-1 leading-relaxed">
          {subtitle}
        </p>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
