import './genlayer-spinner.css'

// The GenLayer mark, held fixed and undistorted — see README for why.
const MARK_PATH =
  'M46.3,27.3 L24,70.7 L47.5,62 L44.4,44.7 Z ' +
  'M53.7,27.3 L76,70.7 L52.5,62 L55.6,44.7 Z ' +
  'M50,54.6 L46.9,63.3 L53.1,63.3 Z'

/**
 * GenLayer Portal "Beacon" spinner.
 *
 * The GenLayer mark sits fixed at the centre, always upright, fill and
 * proportions untouched. All loading motion lives in a Kinetic Cobalt arc
 * that sweeps around it, plus a faint breathing pulse on the mark.
 *
 * @param {number|string} size    Rendered size. A number is treated as px.
 * @param {'default'|'compact'} variant  `compact` drops the orbiting arc —
 *                                use at 16–24px, where the stroke reads as a smudge.
 * @param {boolean} mono          Inherit `currentColor` throughout (mark and
 *                                arc) instead of the brand palette.
 * @param {'auto'|'dark'|'light'} ground  Force a palette on a surface that is
 *                                inverted against the page theme. `auto` follows the theme.
 * @param {string|null} label     Announced to screen readers. Pass `null` when the
 *                                spinner sits beside text that already says it is loading.
 */
export default function GenLayerSpinner({
  size = 48,
  variant = 'default',
  mono = false,
  ground = 'auto',
  label = 'Loading',
  className = '',
  style,
  ...rest
}) {
  const compact = variant === 'compact'

  const classes = [
    'gl-spinner',
    compact && 'gl-spinner--compact',
    mono && 'gl-spinner--mono',
    ground === 'dark' && 'gl-spinner--on-dark',
    ground === 'light' && 'gl-spinner--on-light',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  const a11y = label
    ? { role: 'status', 'aria-label': label }
    : { 'aria-hidden': 'true' }

  return (
    <svg
      className={classes}
      viewBox="0 0 100 100"
      style={{ '--gl-spin-size': typeof size === 'number' ? `${size}px` : size, ...style }}
      {...a11y}
      {...rest}
    >
      {label && <title>{label}</title>}

      {!compact && <circle className="gl-spinner__arc" cx="50" cy="50" r="46" />}
      <path className="gl-spinner__mark" d={MARK_PATH} />
    </svg>
  )
}
