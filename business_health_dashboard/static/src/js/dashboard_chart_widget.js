/** @odoo-module **/

import { Component, onMounted, onPatched, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class BhdChartWidget extends Component {
    static template = "business_health_dashboard.BhdChartWidget";
    static props = { ...standardFieldProps };
    static supportedTypes = ["char", "text"];

    setup() {
        this.canvasRef = useRef("canvas");
        onMounted(() => this._drawChart());
        onPatched(() => this._drawChart());
    }

    _getPayload() {
        const raw = this.props.record.data[this.props.name];
        if (!raw) {
            return null;
        }
        try {
            return JSON.parse(raw);
        } catch {
            return null;
        }
    }

    _drawChart() {
        const canvas = this.canvasRef.el;
        if (!canvas) {
            return;
        }

        const payload = this._getPayload();
        const cssWidth = canvas.clientWidth || 560;
        const cssHeight = 220;
        const dpr = window.devicePixelRatio || 1;

        canvas.width = Math.floor(cssWidth * dpr);
        canvas.height = Math.floor(cssHeight * dpr);
        canvas.style.width = `${cssWidth}px`;
        canvas.style.height = `${cssHeight}px`;

        const ctx = canvas.getContext("2d");
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, cssWidth, cssHeight);

        if (!payload || !payload.labels || !payload.labels.length || !payload.series || !payload.series.length) {
            ctx.fillStyle = "#6b7280";
            ctx.font = "13px sans-serif";
            ctx.fillText("No chart data for this period", 12, 24);
            return;
        }

        const labels = payload.labels;
        const series = payload.series;
        const type = payload.type || "bar";
        const values = series.flatMap((item) => item.values || []);
        const maxAbs = Math.max(1, ...values.map((value) => Math.abs(value)));

        const padding = { top: 16, right: 12, bottom: 34, left: 36 };
        const plotW = cssWidth - padding.left - padding.right;
        const plotH = cssHeight - padding.top - padding.bottom;
        const baselineY = padding.top + plotH;

        ctx.strokeStyle = "#d1d5db";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding.left, padding.top);
        ctx.lineTo(padding.left, baselineY);
        ctx.lineTo(padding.left + plotW, baselineY);
        ctx.stroke();

        if (type === "line") {
            const stepX = labels.length > 1 ? plotW / (labels.length - 1) : 0;
            const s = series[0];
            ctx.strokeStyle = s.color || "#2563eb";
            ctx.lineWidth = 2;
            ctx.beginPath();
            (s.values || []).forEach((value, index) => {
                const x = padding.left + index * stepX;
                const y = baselineY - (value / maxAbs) * plotH;
                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            ctx.stroke();
        } else {
            const groupWidth = plotW / labels.length;
            const seriesCount = series.length;
            const barWidth = Math.max(8, (groupWidth - 8) / Math.max(1, seriesCount));
            labels.forEach((_, labelIndex) => {
                series.forEach((item, seriesIndex) => {
                    const value = (item.values || [])[labelIndex] || 0;
                    const height = (value / maxAbs) * plotH;
                    const x = padding.left + labelIndex * groupWidth + 4 + seriesIndex * barWidth;
                    const y = baselineY - height;
                    ctx.fillStyle = item.color || "#2563eb";
                    ctx.fillRect(x, y, barWidth - 2, height);
                });
            });
        }

        ctx.fillStyle = "#6b7280";
        ctx.font = "11px sans-serif";
        const maxLabels = Math.min(labels.length, 8);
        const interval = Math.max(1, Math.ceil(labels.length / maxLabels));
        labels.forEach((label, index) => {
            if (index % interval !== 0) {
                return;
            }
            const x = padding.left + (index / Math.max(1, labels.length - 1)) * plotW;
            ctx.fillText(label, x - 12, cssHeight - 10);
        });

        let legendX = padding.left;
        const legendY = 10;
        series.forEach((item) => {
            ctx.fillStyle = item.color || "#2563eb";
            ctx.fillRect(legendX, legendY, 10, 10);
            ctx.fillStyle = "#374151";
            ctx.font = "11px sans-serif";
            ctx.fillText(item.label || "Series", legendX + 14, legendY + 9);
            legendX += 80;
        });
    }
}

registry.category("fields").add("bhd_chart_widget", BhdChartWidget);
