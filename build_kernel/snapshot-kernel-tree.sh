#!/usr/bin/env bash
# snapshot-kernel-tree.sh — archive a built Linux tree for later use as a syzkaller target.
#
# Archives: git-tracked sources (working-tree contents, incl. uncommitted edits),
#           vmlinux, boot image, .config, System.map, Module.symvers, *.ko,
#           generated headers, plus a SNAPSHOT_INFO file and a local.patch.
# Skips:    .git and all intermediate build output (*.o, .*.cmd, ...).
#
# Usage:    run inside the kernel source dir
#             ./snapshot-kernel.sh [output-dir]      (default: parent dir)
# Env:      ZSTD_LEVEL (default 3), NO_MODULES=1 to skip *.ko

set -euo pipefail

OUTDIR="${1:-..}"
LEVEL="${ZSTD_LEVEL:-3}"

# --- sanity checks -----------------------------------------------------------
command -v zstd >/dev/null || { echo "error: zstd not installed" >&2; exit 1; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || { echo "error: not inside a git work tree" >&2; exit 1; }
[ "$(git rev-parse --show-toplevel)" = "$(pwd -P)" ] \
  || { echo "error: run this from the top of the kernel tree" >&2; exit 1; }
[ -f vmlinux ] || { echo "error: vmlinux not found (build the kernel first)" >&2; exit 1; }
[ -f Makefile ] && grep -q '^VERSION =' Makefile \
  || echo "warning: this doesn't look like a kernel tree, continuing anyway" >&2
mkdir -p "$OUTDIR"

# --- naming ------------------------------------------------------------------
SHORT=$(git rev-parse --short=12 HEAD)
DIRTY=""
git diff --quiet HEAD || DIRTY="-dirty"
STAMP=$(date +%Y%m%d-%H%M%S)
NAME="linux-snap-${SHORT}${DIRTY}-${STAMP}"
OUT="$(cd "$OUTDIR" && pwd -P)/${NAME}.tar.zst"

# --- metadata (stored at the archive root) -----------------------------------
META=$(mktemp -d)
trap 'rm -rf "$META"' EXIT

git diff HEAD --binary > "$META/local.patch"
UNTRACKED=$(git ls-files --others --exclude-standard | wc -l)

{
  echo "snapshot:        $NAME"
  echo "created:         $(date -Is)"
  echo "host:            $(hostname)"
  echo "build_src_path:  $(pwd -P)"
  echo "git_commit:      $(git rev-parse HEAD)"
  echo "git_describe:    $(git describe --always --dirty 2>/dev/null || true)"
  echo "git_branch:      $(git rev-parse --abbrev-ref HEAD)"
  echo "uncommitted:     $([ -n "$DIRTY" ] && echo 'yes (see local.patch)' || echo no)"
  echo "untracked_files: $UNTRACKED (NOT included)"
  echo "kernelrelease:   $(cat include/config/kernel.release 2>/dev/null || echo unknown)"
  echo "vmlinux_sha256:  $(sha256sum vmlinux | cut -d' ' -f1)"
  echo
  echo "# syzkaller config hint (adjust /new/path to where you extract this):"
  echo "#   \"kernel_obj\":       \"/new/path\","
  echo "#   \"kernel_src\":       \"/new/path\","
  echo "#   \"kernel_build_src\": \"$(pwd -P)\""
} > "$META/SNAPSHOT_INFO"

# --- build file list ---------------------------------------------------------
LIST=$(mktemp)
trap 'rm -rf "$META" "$LIST"' EXIT

git ls-files -z > "$LIST"

add_if_exists() { for f in "$@"; do [ -e "$f" ] && printf '%s\0' "$f" >> "$LIST"; done; return 0; }

add_if_exists vmlinux .config System.map Module.symvers modules.order \
              include/config/kernel.release
# Boot images for whatever arch was built
add_if_exists arch/*/boot/bzImage arch/*/boot/Image arch/*/boot/Image.gz \
              arch/*/boot/zImage arch/*/boot/vmlinuz*

# Generated headers (some coverage lines point into these)
for d in include/generated arch/*/include/generated; do
  [ -d "$d" ] && find "$d" -type f -print0 >> "$LIST"
done

# Kernel modules
if [ "${NO_MODULES:-0}" != "1" ]; then
  find . -path ./.git -prune -o -name '*.ko' -type f -print0 >> "$LIST"
fi

# Drop tracked files that were deleted in the working tree, and de-duplicate
FINAL=$(mktemp)
trap 'rm -rf "$META" "$LIST" "$FINAL"' EXIT
while IFS= read -r -d '' f; do
  f="${f#./}"
  [ -e "$f" ] || [ -L "$f" ] && printf '%s\0' "$f"
done < "$LIST" | sort -zu > "$FINAL"

NFILES=$(tr -cd '\0' < "$FINAL" | wc -c)
echo "Archiving $NFILES files from $(pwd -P)"
[ -n "$DIRTY" ] && echo "note: working tree has uncommitted changes (saved in local.patch, and included as-is)"
[ "$UNTRACKED" -gt 0 ] && echo "note: $UNTRACKED untracked file(s) are NOT included (git status to review)"

# --- archive -----------------------------------------------------------------
tar --null --no-recursion -T "$FINAL" \
    -C "$META" SNAPSHOT_INFO local.patch \
    -I "zstd -T0 -${LEVEL}" -cf "$OUT"

echo
echo "Done: $OUT ($(du -h "$OUT" | cut -f1))"
echo "Extract with: mkdir linux && tar -I zstd -xf $(basename "$OUT") -C linux"