/* globals Chart:false */

(() => {
  'use strict'

  // Graphs
  const ctx = document.getElementById('myChart')
  new Chart(ctx, {
  type: 'line',

  data: {
    datasets: [{
      data: [
        { x:'Enero', y: 1000 },
        { x: 'Febrero', y: 1500 },
        { x: 'Marzo', y: 800 },
        { x: 'Abril', y: 3000 },
        { x: 'Mayo', y: 1200 },
        { x: 'Junio', y: 5000 },
        { x: 'Julio', y: 2000},
        { x: 'Agosto', y: 1000 },
        { x: 'Septiembre', y: 1500 },
        { x: 'Octubre', y: 800 },
        { x: 'Noviembre', y: 3000 },
        { x: 'Diciembre', y: 1200 }
      ],

      borderColor: '#a855f7',
      borderWidth: 4,
      pointBackgroundColor: '#a855f7',
      tension: 0.3
    }]
  },

  options: {
    plugins: {
      legend: {
        display: false
      }
    },
    scales: {
      x: {
        position: 'bottom'
      }
    }
  }
});
})()
