This module adds a  `qty_picked` field on `stock.move.line` to allow scanning
different quantities without having to update the `quantity` field, what would
modify existing reservations.
