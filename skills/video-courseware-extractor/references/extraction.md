# 提取流程与配置

## 一、工具准备与显示坐标

设置 `SKILL_DIR` 为本 Skill 实际安装路径。通过宿主发现 Python/Node/FFmpeg，不写死开发机路径。

```sh
python3 "$SKILL_DIR/scripts/video_slides.py" probe --video "$VIDEO"
```

输出编码尺寸、显示旋转、像素宽高比、帧率、时长及源指纹。扫描器为了避免裁错，遇到旋转不为 0 或非正方形像素会拒绝运行。先用 FFmpeg 自动旋转并按显示比例转换为正方形像素，另存工作副本，保留原片。例如仅有旋转时可用 FFmpeg 默认自动旋转转码并清除 rotate 元数据；非正方形像素用 `scale=trunc(iw*sar/2)*2:ih,setsar=1`，再次 probe 并检查显示。转换后的时间轴必须保持对应，不改变速度或丢掉开头。

## 二、首次取样

已知视频相对时间，用 FFmpeg 取完整显示帧：

```sh
ffmpeg -hide_banner -loglevel error -ss "$SECONDS" -i "$VIDEO" -frames:v 1 -n "$FRAME_PNG"
```

PNG 输出文件名要唯一。核对首、中、尾，确定每段课件区域。相同讲者比例变化时拆成两个 segment；覆盖范围必须能接上，不能让边界出现未检查的空档。

## 三、配置格式

把下面合成示例另存任务私有目录的 `plan.json`，替换文件、讲者、时间和裁切。相对视频路径按 plan 所在目录解析。`output_name` 仅为安全文件名，不含目录。

```json
{
  "schema_version": 1,
  "video": "recording.mp4",
  "sample_fps": 1,
  "stable_seconds": 2,
  "mean_threshold": 2.1,
  "changed_fraction_threshold": 0.017,
  "pixel_threshold": 25,
  "segments": [
    {
      "id": "speaker-a-main",
      "speaker": "讲者甲",
      "output_name": "讲者甲.pptx",
      "start": 15.0,
      "end": 120.0,
      "crop": [100, 80, 960, 720],
      "ignore_regions": [[0.85, 0, 0.15, 0.13]]
    }
  ]
}
```

- `start/end` 是秒，采用 `[start,end)`；起止允许小数。严格递增，段不可重叠，同一讲者可有多段。结束时间不能超过视频时长。
- `crop` 是显示帧像素中的 `[x,y,width,height]`，必须在画面内。不得复用示例坐标。
- `ignore_regions` 为**相对课件裁切框**的 `[x,y,width,height]`，每项 0–1 且不越界。它只用于变化检测，可遮住动态计时器；在此区域出现的新内容可能漏检，因此候选审核仍必须看未经屏蔽的原图。
- 默认阈值来自一类会议录像的经验起点，不是通用判决标准。浅色小字、嵌入视频、持续鼠标移动、弹出菜单需要调阈值或人工划段。

## 四、扫描、审核、高清捕获

```sh
python3 "$SKILL_DIR/scripts/video_slides.py" scan --plan "$PLAN" --out "$NEW_SCAN_JSON"
```

脚本流式读取低分辨率灰度帧，不把数小时全帧装入内存；按课件原比例缩小，保持来源坐标独立。每个候选包含 `begin/end/time/stable`、来源段和裁切；不会自动删除短页或相似页。扫描秒数为近似候选定位值，代表帧必须回看原片确认。

先取候选代表帧供视觉审核，不需要预先填 keep：

```sh
python3 "$SKILL_DIR/scripts/video_slides.py" preview --selection "$NEW_SCAN_JSON" --out-dir "$NEW_PREVIEW_DIR"
```

预览目录含原始彩色整帧及 `review_only: true` 的对照清单，PPT 构建器会拒绝把未审核的预览清单当成成品输入。逐张看图，或用宿主现有图片总览工具生成带候选编号的联系表，再回到整帧确认。preview 不修改扫描 JSON；课件边界和潜在遮挡需要看完整画面。

复制候选 JSON 为 `selected.json`。逐项填 `keep: true/false` 和 `reason`，有必要时修改 `time/crop`。遗漏的短页可手工插入候选，分配唯一 `candidate_id`，记录所在 `segment_id` 和来源区间。页面保留按时间升序；相同时间不同页通常说明选择有误。

```sh
python3 "$SKILL_DIR/scripts/video_slides.py" capture --selection "$SELECTED_JSON" --out-dir "$NEW_CAPTURE_DIR"
```

脚本要求每个候选已决策；按顺序提取整帧 PNG，不绘制、不修补图像。生成 `manifest.json`，其中 `frame` 为整帧、`frame_size` 为显示尺寸、`crop` 为真实课件框；每位讲者独立连续页码。重复输出目录会拒绝，避免混入旧页。精确裁切交给 PPT 原生图片裁切；如需实际裁图，遵从当前宿主图像工具规则。

### 检测质量回查

- 一张页面上依次出现正文、图像、结论：扫描保留变化，审核时按[选页规则](page-selection-and-dedup.md)挑完整代表状态；最后一帧若遮挡正文，选更完整的状态。动态CT只取代表画面，独立CT对照页按内容保留。
- 封面只出现 0.5 秒：1 fps 可能完全采不到。回看讲者开始前后，手工添加代表帧；可针对该短段重扫。
- 布局发生变化：更新该段/该页 crop；把摄像头变化当翻页会产生大量假阳性。
- 仅鼠标/计时器变化：查看完整帧，识别后在检测里排除；不会自动去掉成品里的鼠标/计时器。
- 页面静止但模糊：同页前后取多帧选更清楚的一帧。不要通过锐化编造原本不可辨认的字。
- 回翻前文：来源时间顺序留在私有清单；整理版按选页规则核对整套非相邻重复并去重。用户要求复现讲述顺序时保留回翻。

## 五、截图版 PPT 草稿

`capture` 输出与附带模板契约一致：

```sh
node "$SKILL_DIR/scripts/build_image_decks.mjs" "$MANIFEST" "$NEW_DRAFT_DIR"
```

先按宿主说明让 Node 能解析 `@oai/artifact-tool`，例如在私有工作目录放置模板副本并使用已发现的 node_modules。不要修改全局 Node 配置。模板按每位讲者第一张保留页的课件比例设画布，使用整帧原图和原生 crop，每页保持比例居中，不写备注。它不做去遮挡，也不宣称图片文本可编辑。

若某人封面与正文比例不同，应在 manifest 对应 deck 写入已核对的 `size: [width,height]`，按主体课件比例选择；否则首张封面可能产生不理想留白。16:9 重排应进入修复工作流，不调用截图模板强行拉宽。

查看并逐页修复草稿后，用宿主 presentations 的当前验证流程导出独立正式成品。最终回读，以新版本为准。

## 多个视频文件

本脚本每份 plan 对应一个视频，多个文件各自 probe、扫描、审核、capture，时间均相对各自视频。若同一讲者跨文件讲课，按已核对的文件顺序合并 capture manifest 的对应 deck.pages，重新编号，并将 frame 改成正确的绝对路径（或重新计算相对合并清单的路径）。源文件身份与视频相对时间保留在每页额外的 source_video/source_fingerprint 字段中。不同文件的 time 不能直接排序成一条时间线，页码才是合并后的顺序。合并清单存于私有工作目录，输出名仍每人一份。
