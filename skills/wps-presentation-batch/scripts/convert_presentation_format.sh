#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf '用法: %s <source.pptx|source.pptm> <output-dir>\n' "$0" >&2
}

if [[ $# -ne 2 ]]; then
  usage
  exit 2
fi

source_file=$1
output_dir=$2

if [[ ! -f "$source_file" ]]; then
  printf '源文件不存在: %s\n' "$source_file" >&2
  exit 1
fi

soffice_bin=${SOFFICE_BIN:-$(command -v soffice 2>/dev/null || true)}
if [[ -z "$soffice_bin" || ! -x "$soffice_bin" ]]; then
  printf '缺少 soffice，请通过 SOFFICE_BIN 传入可用的绝对路径\n' >&2
  exit 1
fi

source_name=$(basename "$source_file")
stem=${source_name%.*}
extension=$(printf '%s' "${source_name##*.}" | tr '[:upper:]' '[:lower:]')

case "$extension" in
  pptx)
    target_extension=pptm
    convert_format=pptm
    ;;
  pptm)
    target_extension=pptx
    convert_format=pptx
    ;;
  *)
    printf '只支持 PPTX 与 PPTM，收到: .%s\n' "$extension" >&2
    exit 2
    ;;
esac

mkdir -p "$output_dir"
target_path="${output_dir%/}/${stem}.${target_extension}"
if [[ -e "$target_path" ]]; then
  printf '目标文件已存在，为避免覆盖而停止: %s\n' "$target_path" >&2
  exit 1
fi

"$soffice_bin" --headless --convert-to "$convert_format" --outdir "$output_dir" "$source_file"

if [[ ! -f "$target_path" || ! -s "$target_path" ]]; then
  printf '转换命令结束，但未找到有效目标文件: %s\n' "$target_path" >&2
  exit 1
fi

printf '%s\n' "$target_path"
