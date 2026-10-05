"use client";

import React from "react";
import { ActivityFeedEvent } from "@/lib/api";

interface ActivityStreamProps {
  events: ActivityFeedEvent[];
  syncChoiceText: string;
}

export default function ActivityStream({ events, syncChoiceText }: ActivityStreamProps) {
  if (!events || events.length === 0) return null;

  return (
    <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-4 my-5 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
      {/* Stream Header */}
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#10B981] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#10B981]"></span>
          </span>
          <strong className="text-[14px] text-[#0F172A] font-bold">
            ⚡ Real-Time Activity Feed
          </strong>
          <span className="text-[11.5px] text-[#64748B]">
            ({events.length} live telemetry events recorded)
          </span>
        </div>
        <div className="text-[11px] text-[#059669] font-semibold bg-[#ECFDF5] px-2.5 py-1 rounded-full border border-[#A7F3D0]">
          ● Live Sync: {syncChoiceText}
        </div>
      </div>

      {/* Event Cards */}
      <div className="space-y-2">
        {events.slice(0, 6).map((ev) => {
          let badgeStyle = "bg-[#EFF6FF] text-[#1D4ED8] border-[#BFDBFE]";
          if (ev.event_type === "email_opened") {
            badgeStyle = "bg-[#E0F2FE] text-[#0369A1] border-[#BAE6FD]";
          } else if (ev.event_type === "reply_received") {
            badgeStyle = "bg-[#F3E8FF] text-[#6D28D9] border-[#DDD6FE]";
          } else if (ev.event_type === "meeting_booked") {
            badgeStyle = "bg-[#ECFDF5] text-[#047857] border-[#A7F3D0]";
          }

          return (
            <div
              key={ev.id}
              className="bg-white border border-[#E2E8F0] rounded-lg px-3.5 py-2.5 flex items-center justify-between flex-wrap gap-2 shadow-[0_1px_2px_rgba(0,0,0,0.02)] hover:border-[#CBD5E1] transition-colors"
            >
              <div className="flex items-center gap-2.5 flex-wrap">
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${badgeStyle}`}>
                  {ev.badge}
                </span>
                <strong className="text-[13px] text-[#0F172A] font-semibold">
                  {ev.name || "Lead"}
                </strong>
                <span className="text-[12px] text-[#64748B]">
                  ({ev.email})
                </span>
                {ev.company && (
                  <span className="bg-[#F1F5F9] text-[#475569] text-[11px] px-2 py-0.5 rounded border border-[#E2E8F0]">
                    {ev.company}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[12px] text-[#475569] font-medium">
                  {ev.details}
                </span>
                <span className="text-[11px] text-[#64748B] bg-[#F8FAFC] px-2 py-0.5 rounded border border-[#E2E8F0]">
                  ⏱️ {ev.relative_time || "just now"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
