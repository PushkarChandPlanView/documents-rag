import { SVGProps, Ref } from "react";
import { withIconWrapper } from "@planview/pv-icons";
import React from "react";

const SlackIconSvg = (props: SVGProps<SVGSVGElement>, ref: Ref<SVGSVGElement>) => (
  <svg
    viewBox="0 0 16 16"
    xmlns="http://www.w3.org/2000/svg"
    preserveAspectRatio="xMidYMid meet"
    focusable="false"
    color="var(--pvdsuikit__button--emptyinverse--normal__icon, #fff)"
    ref={ref}
    {...props}
  >
    {/* bottom-left arm */}
    <path d="M5.042 10.166a1.458 1.458 0 0 1-1.456 1.456 1.458 1.458 0 0 1-1.456-1.456 1.458 1.458 0 0 1 1.456-1.455h1.456v1.455z" fill="currentColor" />
    <path d="M5.77 10.166a1.458 1.458 0 0 1 1.456-1.455 1.458 1.458 0 0 1 1.455 1.455v3.64a1.458 1.458 0 0 1-1.455 1.456 1.458 1.458 0 0 1-1.456-1.456v-3.64z" fill="currentColor" />
    {/* top-left arm */}
    <path d="M7.226 5.042a1.458 1.458 0 0 1-1.456-1.456 1.458 1.458 0 0 1 1.456-1.456 1.458 1.458 0 0 1 1.455 1.456v1.456H7.226z" fill="currentColor" />
    <path d="M7.226 5.77a1.458 1.458 0 0 1 1.455 1.456 1.458 1.458 0 0 1-1.455 1.455H3.586a1.458 1.458 0 0 1-1.456-1.455 1.458 1.458 0 0 1 1.456-1.456h3.64z" fill="currentColor" />
    {/* top-right arm */}
    <path d="M12.35 7.226a1.458 1.458 0 0 1 1.456-1.456 1.458 1.458 0 0 1 1.456 1.456 1.458 1.458 0 0 1-1.456 1.455H12.35V7.226z" fill="currentColor" />
    <path d="M11.622 7.226a1.458 1.458 0 0 1-1.455 1.455 1.458 1.458 0 0 1-1.456-1.455V3.586a1.458 1.458 0 0 1 1.456-1.456 1.458 1.458 0 0 1 1.455 1.456v3.64z" fill="currentColor" />
    {/* bottom-right arm */}
    <path d="M10.166 12.35a1.458 1.458 0 0 1 1.456 1.456 1.458 1.458 0 0 1-1.456 1.456 1.458 1.458 0 0 1-1.455-1.456V12.35h1.455z" fill="currentColor" />
    <path d="M10.166 11.622a1.458 1.458 0 0 1-1.455-1.456 1.458 1.458 0 0 1 1.455-1.455h3.64a1.458 1.458 0 0 1 1.456 1.455 1.458 1.458 0 0 1-1.456 1.456h-3.64z" fill="currentColor" />
  </svg>
);

const SlackIcon = React.forwardRef(SlackIconSvg);

export const CustomSlackIcon = withIconWrapper(SlackIcon, 'slack-icon');
