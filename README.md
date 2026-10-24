# 焊缝跟踪教学演示

一个无需安装依赖、可在浏览器运行的教学项目，用来讲解结构光视觉焊缝跟踪的基本流程：采集轮廓、提取特征点、坐标转换和机器人路径修正。

## 功能

- 拼接焊、圆弧路径、搭接焊、直角焊四种示意
- 调整工件横向/纵向偏移和旋转角度
- 在一张融合俯视图中同时显示工件、焊缝路径、红色激光扫描线和修正轨迹
- 演示截面采集、特征点提取、坐标转换与路径修正
- 附带可处理激光条纹图像的 Python/OpenCV 算法：预处理、亚像素中心线、V 形坡口底端和搭接台阶拐点检测
- 纯静态网页，无需安装依赖、构建工具或连接设备

## 几何说明

- **拼接焊**：两块板处于同一平面，边缘相对形成接缝。
- **圆弧路径**：表示沿弧形接缝运动的路径示例；它描述路径形状，不是基本接头类别。截面轮廓为教学示意，真实轮廓应按工件和传感器实际视角确定。
- **搭接焊**：两板实际重叠，示意焊缝沿上板搭接边缘。
- **直角焊**：按参考样式表现为 T 形接头角焊缝，一块立板垂直放在底板上，焊缝沿两板交界线延伸。

融合俯视图把工件、焊缝、初始/修正路径和激光扫描位置放在同一画面中，便于比较它们的位置关系。截面图用于解释轮廓特征点。

## 使用方式

1. 在 GitHub 仓库页面点击 **Code → Download ZIP** 并解压。
2. 确认 `index.html`、`style.css` 和 `app.js` 位于同一文件夹。
3. 双击 `index.html`，使用 Edge 或 Chrome 打开。无需联网或安装软件。

## 图像处理算法

`vision_algorithms.py` 提供可直接调用的图像处理函数。它先按 ROI 裁剪并用高斯滤波降噪，再以逐列相对阈值生成激光条纹掩膜；随后用灰度重心法计算亚像素中心线，并通过连续性约束抑制跳点。

详细原理、计算公式、参数含义和适用范围见 [算法原理说明](算法原理说明.md)。

- `preprocess_laser_stripe`：灰度化、ROI、滤波和二值掩膜。
- `extract_centerline`：沿图像列提取激光条纹亚像素中心线。
- `detect_v_groove_bottom`：对 V 形两侧分段拟合直线，以交点作为坡口根部候选。
- `detect_lap_step_corner`：在中心线上检测搭接截面的高度突变点。
- `pixel_to_robot_xy`：用已标定的 3×3 单应矩阵将像素点映射到机器人平面坐标。
- `draw_algorithm_overlay`：绘制中心线和检测到的特征点，方便检查。

安装可选依赖后，可对相机采集图像运行示例：

```bash
python -m pip install -r requirements-vision.txt
python examples/run_vision_algorithms.py path/to/laser-image.png --feature v-groove --roi 100 50 500 300
python examples/run_vision_algorithms.py path/to/laser-image.png --feature lap-step
```

算法输出的是图像中的特征候选点。实际效果取决于曝光、反光、遮挡、扫描视角和 ROI；`confidence` 是用于比较候选结果的启发式分数，不是概率。接入机器人前还需完成相机/传感器标定、手眼标定、坐标系转换和安全验证。

## 使用建议

1. 选择焊缝类型，引导读者识别可能用于跟踪的边缘、交点或中心特征。
2. 调整偏移和旋转，请先预测焊缝位置，再观察演示。
3. 讨论感知、坐标转换、路径修正和安全停止对应的程序阶段。
4. 对比不同接头的特征点和路径形式，填写实验记录。

## 范围与限制

网页部分是概念演示，不与 ABB1410、机器人控制器、英莱相机或焊机通信。Python 模块提供基础图像算法示例，不包含厂商设备接口、实时跟踪控制、手眼标定或安全联锁。网页中的工件、扫描线、截面和路径均为示意；图像算法需要用实际相机图像调整参数。接入设备前，应完成标定与坐标系验证，并由设备负责人审核安全联锁。

几何定义参考 [Miller Welds 焊接接头类型资料](https://www.millerwelds.com/-/media/miller-electric/files/pdf/articles/jointypes.pdf) 和 [AWS A2.4 焊接符号图表](https://app.aws.org/mwf/attachments/64/225364/AWSWeldSymbolchart.pdf)。

## 文件结构

```text
index.html   页面结构
style.css    样式
app.js       焊缝示意与交互逻辑
vision_algorithms.py  激光条纹预处理与特征提取算法
requirements-vision.txt  图像算法依赖
examples/run_vision_algorithms.py  单张图像运行示例
算法原理说明.md  处理流程、公式与使用边界
```

## License

本项目采用 [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)。仅允许非商业用途；商业使用需要另行取得许可。详见 [LICENSE](LICENSE)。

