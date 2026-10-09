#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf '用法: %s <source.pptx|source.pptm|source.ppt> <count> <output-dir> [base-name]\n' "$0" >&2
}

if [[ $# -lt 3 || $# -gt 4 ]]; then
  usage
  exit 2
fi

source_file=$1
requested_count=$2
output_dir=$3
source_name=$(basename "$source_file")
stem=${source_name%.*}
output_base=${4:-$stem}

if [[ ! -f "$source_file" ]]; then
  printf '源文件不存在: %s\n' "$source_file" >&2
  exit 1
fi

if [[ ! "$requested_count" =~ ^[1-9][0-9]*$ ]]; then
  printf '页数必须是正整数: %s\n' "$requested_count" >&2
  exit 2
fi

soffice_bin=${SOFFICE_BIN:-$(command -v soffice 2>/dev/null || true)}
pdftoppm_bin=${PDFTOPPM_BIN:-$(command -v pdftoppm 2>/dev/null || true)}
pdfinfo_bin=${PDFINFO_BIN:-$(command -v pdfinfo 2>/dev/null || true)}

for required in soffice_bin pdftoppm_bin pdfinfo_bin; do
  if [[ -z ${!required} || ! -x ${!required} ]]; then
    printf '缺少可执行文件，请设置对应环境变量: %s\n' "$required" >&2
    exit 1
  fi
done

mkdir -p "$output_dir"

tmpdir=$(mktemp -d -t wps-ppt-render)
cleanup() {
  rm -rf -- "$tmpdir"
}
trap cleanup EXIT

"$soffice_bin" --headless --convert-to pdf --outdir "$tmpdir" "$source_file"
pdf_path=$(find "$tmpdir" -maxdepth 1 -type f -name '*.pdf' -print -quit)
if [[ -z "$pdf_path" ]]; then
  printf '未生成 PDF，无法渲染: %s\n' "$source_file" >&2
  exit 1
fi

total_pages=$(
  "$pdfinfo_bin" "$pdf_path" | awk '/^Pages:/ { print $2; exit }'
)
if [[ ! "$total_pages" =~ ^[1-9][0-9]*$ ]]; then
  printf '无法读取 PDF 页数: %s\n' "$pdf_path" >&2
  exit 1
fi
if (( requested_count > total_pages )); then
  printf '请求导出 %s 页，但源文件只有 %s 页\n' "$requested_count" "$total_pages" >&2
  exit 1
fi

for ((i = 1; i <= requested_count; i++)); do
  output_path="${output_dir%/}/${output_base}-第${i}页.png"
  if [[ -e "$output_path" ]]; then
    printf '目标文件已存在，为避免覆盖而停止: %s\n' "$output_path" >&2
    exit 1
  fi
done

"$pdftoppm_bin" -png -r 180 -f 1 -l "$requested_count" "$pdf_path" "$tmpdir/slide"

for ((i = 1; i <= requested_count; i++)); do
  rendered_path="$tmpdir/slide-${i}.png"
  output_path="${output_dir%/}/${output_base}-第${i}页.png"
  if [[ ! -f "$rendered_path" ]]; then
    printf '第 %s 页渲染结果不存在\n' "$i" >&2
    exit 1
  fi
  cp "$rendered_path" "$output_path"
  if [[ ! -s "$output_path" ]]; then
    printf '输出文件为空: %s\n' "$output_path" >&2
    exit 1
  fi
  printf '%s\n' "$output_path"
done
