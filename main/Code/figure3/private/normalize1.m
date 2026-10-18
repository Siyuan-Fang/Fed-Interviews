function P = normalize1(C, vrange)
% PURPOSE: Reorder the rows of C and flip their signs according to a rule.
% INPUTS:
% C - matrix to reorder and flip
% vrange - column numbers: after reordering and flipping the average of
%          these columns will be positive in each row
% OUTPUT:
% P - the matrix that reorders the rows of C and flips their signs
% so that P*C will satisfy:
% 1) The average of vrange of each row is positive
% 2) Each consecutive diagonal element is as large as possible

% 1) The average of vrange of each row is positive
P = diag(sign(mean(C(:,vrange),2)));

% 2) Each consecutive diagonal element is as large as possible
N = size(C,1);
idx = nan(1,N);
temp = abs(C);
for n = 1:N
    [~, i] = max(temp(:,n));
    idx(n) = i;
    temp(i,:) = -inf;
end
P = P(idx,:);

