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

export const isSuperAdmin = (user) => {
  if (!user) {
    return false;
  }
  const positionSlug = user?.position?.slug;
  if (positionSlug && positionSlug.toLowerCase() === 'super-admin') {
    return true;
  }
  return user.role === 'admin' && !positionSlug;
};
