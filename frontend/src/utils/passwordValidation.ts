export const PASSWORD_REQUIREMENTS = [
  'At least 8 characters',
  'At least one uppercase letter',
  'At least one special character',
] as const

export function validatePassword(password: string): string | null {
  if (password.length < 8) {
    return 'Password must be at least 8 characters'
  }
  if (!/[A-Z]/.test(password)) {
    return 'Password must contain at least one uppercase letter'
  }
  if (!/[^A-Za-z0-9]/.test(password)) {
    return 'Password must contain at least one special character'
  }
  return null
}
