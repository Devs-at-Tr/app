export const hasPermission = (user, permission) => {
  if (!permission) {
    return true;
  }
  if (!user) {
    return false;
  }
  if (user.role === 'admin') {
    return true;
  }
  return Array.isArray(user.permissions) && user.permissions.includes(permission);
};

export const hasAnyPermission = (user, permissions = []) => {
  if (!permissions.length) {
    return true;
  }
  return permissions.some((permission) => hasPermission(user, permission));
};
