// A failed transport is not authoritative evidence that the server revoked a
// session. The caller must still withhold protected UI until verification.
export const sessionWasRejected = error => error?.status === 401 || error?.status === 403;
