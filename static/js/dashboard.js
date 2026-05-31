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

/* ── Polling de notificaciones cada 10 segundos ─────────────── */
const ICONOS_MOV = {
  ENTRADA:  'fa-arrow-up',
  VENTA:    'fa-cart-shopping',
  ANULACION:'fa-rotate-left',
  AJUSTE:   'fa-sliders',
}

function construirItemAlerta(clase, icono, titulo, sub) {
  return `<div class="notif-item">
    <div class="notif-icon ${clase}"><i class="fa-solid ${icono}"></i></div>
    <div class="notif-text">
      <div class="notif-title">${titulo}</div>
      <div class="notif-sub">${sub}</div>
    </div>
  </div>`
}

function actualizarNotificaciones() {
  fetch('/auth/notificaciones-json')
    .then(r => r.json())
    .then(data => {
      const badge = document.getElementById('notif-badge')
      const feed  = document.getElementById('notif-feed')
      if (!badge || !feed) return

      // Actualizar badge
      if (data.total_alertas > 0) {
        badge.textContent = data.total_alertas
        badge.style.display = ''
      } else {
        badge.style.display = 'none'
      }

      // Construir ítems
      let html = ''

      data.libros_roja.forEach(l => {
        html += construirItemAlerta('roja', 'fa-triangle-exclamation',
          l.nombre, `Stock crítico · ${l.stock} unidad(es)`)
      })

      data.libros_amarilla.forEach(l => {
        html += construirItemAlerta('amarilla', 'fa-circle-exclamation',
          l.nombre, `Stock bajo · ${l.stock} unidades`)
      })

      data.movimientos.forEach(m => {
        const icono = ICONOS_MOV[m.tipo] || 'fa-sliders'
        const sub   = `${m.cantidad} uds · ${m.fecha}${m.motivo ? ' · ' + m.motivo : ''}`
        html += construirItemAlerta('mov', icono, `${m.tipo}: ${m.libro}`, sub)
      })

      if (!html) {
        html = `<div class="notif-empty">
          <i class="fa-regular fa-bell-slash"></i>
          Sin notificaciones recientes
        </div>`
      }

      feed.innerHTML = html
    })
    .catch(() => {}) // falla silenciosa si no hay red
}

setInterval(actualizarNotificaciones, 10000)
