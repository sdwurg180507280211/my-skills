#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf '用法: %s <source.pptx|source.pptm|source.ppt> <count|first-last> <output-dir> [base-name]\n' "$0" >&2
  printf '  count 导出前 N 页；first-last 导出指定页码范围，例如 3-7\n' >&2
}

if [[ $# -lt 3 || $# -gt 4 ]]; then
  usage
  exit 2
fi

source_file=$1
page_spec=$2
output_dir=$3
source_name=$(basename "$source_file")
stem=${source_name%.*}
output_base=${4:-$stem}

if [[ ! -f "$source_file" ]]; then
  printf '源文件不存在: %s\n' "$source_file" >&2
  exit 1
fi

if [[ "$page_spec" =~ ^([1-9][0-9]*)-([1-9][0-9]*)$ ]]; then
  first_page=${BASH_REMATCH[1]}
  last_page=${BASH_REMATCH[2]}
elif [[ "$page_spec" =~ ^[1-9][0-9]*$ ]]; then
  first_page=1
  last_page=$page_spec
else
  printf '页数必须是正整数或 first-last 范围: %s\n' "$page_spec" >&2
  exit 2
fi
if (( first_page > last_page )); then
  printf '起始页大于结束页: %s\n' "$page_spec" >&2
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

# A private profile keeps an already running LibreOffice from swallowing the job silently.
"$soffice_bin" -env:UserInstallation="file://$tmpdir/lo-profile" --headless \
  --convert-to pdf --outdir "$tmpdir" "$source_file"
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
if (( last_page > total_pages )); then
  printf '请求导出到第 %s 页，但源文件只有 %s 页\n' "$last_page" "$total_pages" >&2
  exit 1
fi

for ((i = first_page; i <= last_page; i++)); do
  output_path="${output_dir%/}/${output_base}-第${i}页.png"
  if [[ -e "$output_path" ]]; then
    printf '目标文件已存在，为避免覆盖而停止: %s\n' "$output_path" >&2
    exit 1
  fi
done

"$pdftoppm_bin" -png -r "${RENDER_DPI:-180}" -f "$first_page" -l "$last_page" "$pdf_path" "$tmpdir/slide"

for ((i = first_page; i <= last_page; i++)); do
  # pdftoppm zero-pads page numbers to the width of the last page number.
  rendered_path=$(find "$tmpdir" -maxdepth 1 -type f -name "slide-*.png" | awk -v n="$i" '{ f=$0; sub(/.*slide-0*/, "", f); sub(/\.png$/, "", f); if (f == n) print $0 }' | head -n 1)
  output_path="${output_dir%/}/${output_base}-第${i}页.png"
  if [[ -z "$rendered_path" || ! -f "$rendered_path" ]]; then
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
