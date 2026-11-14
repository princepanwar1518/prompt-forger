export const VERSION = "1.2.0";
export const REPO_URL = "https://github.com/princepanwar1518/prompt-forger";
const RELEASE = `${REPO_URL}/raw/main/releases/v${VERSION}`;

export interface Download {
  id: string;
  os: "Windows" | "macOS";
  title: string;
  detail: string;
  file: string;
  size: string;
  href: string;
  primary?: boolean;
}

export const DOWNLOADS: Download[] = [
  {
    id: "win-setup",
    os: "Windows",
    title: "Windows installer",
    detail: "Windows 10/11, 64-bit. No admin rights needed. Upgrades older versions in place.",
    file: `PromptForger-Setup-${VERSION}.exe`,
    size: "46 MB",
    href: `${RELEASE}/PromptForger-Setup-${VERSION}.exe`,
    primary: true,
  },
  {
    id: "win-portable",
    os: "Windows",
    title: "Windows portable",
    detail: "No install: unzip and run PromptForger.exe.",
    file: `PromptForger-${VERSION}-windows-portable.zip`,
    size: "53 MB",
    href: `${RELEASE}/PromptForger-${VERSION}-windows-portable.zip`,
  },
  {
    id: "mac-arm",
    os: "macOS",
    title: "Mac (Apple Silicon)",
    detail: "M1, M2, M3, M4. Unzip and drag Prompt Forger to Applications.",
    file: `PromptForger-${VERSION}-mac-arm64.zip`,
    size: "53 MB",
    href: `${RELEASE}/PromptForger-${VERSION}-mac-arm64.zip`,
    primary: true,
  },
  {
    id: "mac-intel",
    os: "macOS",
    title: "Mac (Intel)",
    detail: "Intel Macs. Unzip and drag Prompt Forger to Applications.",
    file: `PromptForger-${VERSION}-mac-x64.zip`,
    size: "55 MB",
    href: `${RELEASE}/PromptForger-${VERSION}-mac-x64.zip`,
  },
];

export const CHECKSUMS_URL = `${RELEASE}/SHA256SUMS.txt`;
