const colorStops = [
    [-4, '#990000'],
    [-3, '#b30000'],
    [-2, '#ff0000'],
    [-1, '#ff1a1a'],
    [0, '#c5c3c3'],
    [1, '#47d147'],
    [2, '#33cc33'],
    [3, '#29a329'],
    [4, '#29a329']
];

fetch('/get_data')
    .then(response => response.json())
    .then(data => {
        Highcharts.chart('container', {
            chart: {
                type: 'treemap',
                height: '460px', // Make the chart fill the height of the container
                // width: '100%', // Make the chart fill the width of the container
                spacing: [0, 0, 0, 0],
                backgroundColor: 'transparent'
            },
            title: {  // Set title explicitly to empty
                text: null
            },
            colorAxis: {
                stops: colorStops.map(([value, color]) => [((value + 4) / 8), color]),
                min: -4,
                max: 4,
            },
            legend: {
                enabled: false
            },
            series: [{
                type: 'treemap',
                layoutAlgorithm: 'squarified',
                dataLabels: {
                    enabled: true,
                    useHTML: true,
                    formatter: function() {
                        const point = this.point;
                        const shapeArgs = point.shapeArgs || {};
                        const width = shapeArgs.width || 0;
                        const height = shapeArgs.height || 0;
                        const minDimension = Math.min(width, height);
                        const imgSize = Math.min(48, minDimension * 0.5);
                        const fontSize = Math.max(6, Math.min(14, minDimension / 8));
                        const [symbol, price, change] = point.name.split('|');

                        let content = `<img src="${point.image}" class="circle-img" style="width:${imgSize}px;height:${imgSize}px;object-fit:contain;">`;
                        
                        if (minDimension >= 60) {
                            content += `
                                <div style="font-weight:bold;font-size:${fontSize}px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;text-align:center;">${symbol}</div>
                                <div style="font-size:${fontSize * 0.9}px;text-align:center;">${price}</div>
                                <div style="font-size:${fontSize * 0.9}px;text-align:center;">${change}</div>
                            `;
                        }

                        return `<div style="width:${width}px;height:${height}px;display:flex;flex-direction:column;justify-content:center;align-items:center;overflow:hidden;padding:2px;box-sizing:border-box;">
                            ${content}
                        </div>`;
                    },
                    style: {
                        color: '#ffffff',
                        textOutline: 'none',
                    },
                    padding: 0,
                    allowOverlap: true
                },
                data: data
            }],
            // Remove the title property entirely for no title display
            tooltip: {
                useHTML: true,
                formatter: function() {
                    const [symbol, price, change] = this.point.name.split('|');
                    return `<b>${symbol}</b><br/>Price: ${price}<br/>Change: ${change}`;
                },
                positioner: function(labelWidth, labelHeight, point) {
                    return {
                        x: point.plotX + 10,
                        y: point.plotY - labelHeight - 10
                    };
                }
            },
            // Disable exporting to remove the menu button in the top right
            exporting: {
                enabled: false
            }
        });
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('container').innerHTML = 'Error loading data. Please check the console for details.';
    });
