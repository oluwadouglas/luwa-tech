/** @odoo-module **/

import { Component, onWillStart, onMounted, proxy, signal } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class LalaaLoanDashboard extends Component {
    portfolioChartRef = signal.ref();
    collectionsChartRef = signal.ref();
    Math = Math;
    Object = Object;

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = proxy({
            data: null,
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            if (this.state.data) {
                this.renderCharts();
            }
        });
    }

    async loadData() {
        this.state.isLoading = true;
        try {
            this.state.data = await this.orm.call(
                "lalaa.loan.dashboard",
                "get_dashboard_data",
                [{}]
            );
        } catch (e) {
            console.error("Dashboard error", e);
        } finally {
            this.state.isLoading = false;
        }
    }

    openActiveLoans() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Active Loans",
            res_model: "lalaa.loan",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "active"]],
        });
    }

    openPendingApplications() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Pending Applications",
            res_model: "lalaa.loan.application",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "not in", ["approved", "rejected"]]],
        });
    }

    formatCurrency(value) {
        if (!value) return "UGX 0";
        return new Intl.NumberFormat('en-UG', {
            style: 'currency',
            currency: 'UGX',
            maximumFractionDigits: 0
        }).format(value);
    }

    formatPercent(value) {
        if (value === undefined || value === null) return "0.0%";
        return `${value.toFixed(1)}%`;
    }

    renderCharts() {
        const chartTextColor = 'rgba(255, 255, 255, 0.8)';
        
        if (this.portfolioChartRef()) {
            new Chart(this.portfolioChartRef(), {
                type: 'doughnut',
                data: {
                    labels: ['Healthy', 'PAR>30', 'PAR>90 (NPL)'],
                    datasets: [{
                        data: [
                            this.state.data.headline.gross_loan_portfolio - (this.state.data.portfolio.par_30_ratio/100 * this.state.data.headline.gross_loan_portfolio),
                            this.state.data.portfolio.par_30_ratio/100 * this.state.data.headline.gross_loan_portfolio,
                            this.state.data.portfolio.par_90_ratio/100 * this.state.data.headline.gross_loan_portfolio
                        ],
                        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                        borderWidth: 0,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { 
                            position: 'bottom',
                            labels: { color: chartTextColor }
                        }
                    }
                }
            });
        }
        
        if (this.collectionsChartRef()) {
            new Chart(this.collectionsChartRef(), {
                type: 'bar',
                data: {
                    labels: ['1-30 Days', '31-60 Days', '61-90 Days', '>90 Days'],
                    datasets: [{
                        label: 'Amount in Arrears',
                        data: [
                            this.state.data.collections.aging_brackets['1_30'],
                            this.state.data.collections.aging_brackets['31_60'],
                            this.state.data.collections.aging_brackets['61_90'],
                            this.state.data.collections.aging_brackets['90_plus'],
                        ],
                        backgroundColor: '#3b82f6',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: chartTextColor }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: chartTextColor },
                            grid: { color: 'rgba(255, 255, 255, 0.1)' }
                        },
                        y: { 
                            beginAtZero: true,
                            ticks: { color: chartTextColor },
                            grid: { color: 'rgba(255, 255, 255, 0.1)' }
                        }
                    }
                }
            });
        }
    }
}

LalaaLoanDashboard.template = "lalaa_loan_dashboard.MainDashboard";

registry.category("actions").add("lalaa_loan_dashboard.main", LalaaLoanDashboard);
